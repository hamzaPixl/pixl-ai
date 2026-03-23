"""Database connection management and initialization.

Handles SQLite connection lifecycle, WAL mode, pragmas,
schema creation, and version-based migrations.

PixlDB implements the StorageBackend protocol — callers should
type-hint against StorageBackend, not PixlDB directly. This
allows swapping the storage backend without changing call sites.

THREAD SAFETY: PixlDB uses thread-local storage for connections.
Each thread gets its own SQLite connection to avoid threading issues
when used in multi-threaded contexts like FastAPI's thread pool.
"""

import contextlib
import importlib
import sqlite3
import stat
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pixl.paths import get_pixl_dir
from pixl.storage.db.schema import SCHEMA_VERSION, get_schema_sql
from pixl.storage.protocols import (
    ArtifactStore,
    BacklogStore,
    EventStore,
    KnowledgeStore,
    SessionStore,
)


class _ThreadLocalConn(threading.local):
    """Thread-local storage for SQLite connections.

    Each thread gets its own connection to the same database file.
    This prevents sqlite3.InterfaceError when multiple threads
    access the database concurrently (e.g., FastAPI thread pool).

    IMPORTANT: Do NOT add __slots__ here. Slots on threading.local
    subclasses create class-level descriptors that are shared across
    all threads, completely defeating thread isolation.
    """

    conn: sqlite3.Connection | None

    def __init__(self) -> None:
        self.conn = None


class PixlDB:
    """SQLite implementation of StorageBackend.

    Provides access to all domain-specific stores through
    lazy-loaded properties. Thread-local connections for
    safe concurrent access, WAL mode for concurrent reads.

    Usage:
        # Callers should depend on the protocol, not the class:
        def do_work(db: StorageBackend) -> None:
            db.backlog.add_feature(...)

        # Only the factory creates the concrete instance:
        db = PixlDB(project_path)
        db.initialize()
        do_work(db)
    """

    def __init__(
        self,
        project_path: Path,
        *,
        pixl_dir: Path | None = None,
        on_event_commit: "Callable[[], None] | None" = None,
    ) -> None:
        self.project_path = project_path
        self.pixl_dir = pixl_dir if pixl_dir is not None else get_pixl_dir(project_path)
        self.db_path = self.pixl_dir / "pixl.db"
        self._on_event_commit = on_event_commit
        self._event_bus: Any = None  # Optional EventBus for real-time event distribution

        # Thread-local storage for connections - each thread gets its own
        self._thread_local = _ThreadLocalConn()

        # SQLite WAL allows concurrent reads but only one writer at a time;
        # this lock avoids relying solely on busy_timeout for in-process
        # contention between thread-local connections.
        self._write_lock = threading.Lock()

        # Lazy-loaded stores (typed against protocols for encapsulation)
        # Note: These are shared across threads, but each holds a reference
        # to this PixlDB instance, which provides thread-local connections.
        self._stores: dict[str, Any] = {}

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create thread-local database connection.

        This is SQLite-specific and NOT part of the StorageBackend protocol.
        Only internal/migration code should use this.

        Each thread gets its own connection to avoid threading issues
        with SQLite when used in multi-threaded contexts like FastAPI.
        """
        if self._thread_local.conn is None:
            self._thread_local.conn = self._connect()
        conn = self._thread_local.conn
        assert conn is not None, "Failed to create thread-local SQLite connection"
        return conn

    @contextlib.contextmanager
    def write(self):
        """Context manager for serialized write access.

        Acquires ``_write_lock``, yields the thread-local connection,
        and auto-commits on success or rolls back on error.
        """
        with self._write_lock:
            conn = self.conn
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def _lazy_store(self, name: str, module: str, cls_name: str, **kwargs) -> Any:
        """Lazily instantiate and cache a domain store.

        Replaces per-property boilerplate with a single lookup pattern.
        Thread-safe because store instances delegate to thread-local
        connections via self.conn.
        """
        cached = self._stores.get(name)
        if cached is None:
            mod = importlib.import_module(module)
            cached = getattr(mod, cls_name)(self, **kwargs)
            self._stores[name] = cached
        return cached

    def set_event_bus(self, bus: Any) -> None:
        """Attach an EventBus for real-time event distribution.

        Must be called before first access to ``self.events`` (before the
        lazy store is created).  If the events store was already created,
        the bus is injected directly.
        """
        self._event_bus = bus
        # If events store already instantiated, inject the bus
        if "events" in self._stores:
            self._stores["events"]._event_bus = bus

    @property
    def backlog(self) -> BacklogStore:
        return self._lazy_store("backlog", "pixl.storage.db.backlog", "BacklogDB")

    @property
    def knowledge(self) -> KnowledgeStore:
        return self._lazy_store("knowledge", "pixl.storage.db.knowledge", "KnowledgeDB")

    @property
    def artifacts(self) -> ArtifactStore:
        return self._lazy_store("artifacts", "pixl.storage.db.artifacts", "ArtifactDB")

    @property
    def events(self) -> EventStore:
        return self._lazy_store(
            "events",
            "pixl.storage.db.events",
            "EventDB",
            on_commit=self._on_event_commit,
            event_bus=self._event_bus,
        )

    @property
    def sessions(self) -> SessionStore:
        return self._lazy_store("sessions", "pixl.storage.db.sessions", "SessionDB")

    @property
    def session_reports(self):
        return self._lazy_store(
            "session_reports", "pixl.storage.db.session_reports", "SessionReportDB"
        )

    @property
    def incidents(self):
        return self._lazy_store("incidents", "pixl.storage.db.incidents", "IncidentDB")

    @property
    def metrics(self):
        return self._lazy_store("metrics", "pixl.storage.db.metrics", "MetricsStore")

    @property
    def chain_signals(self):
        return self._lazy_store("chain_signals", "pixl.storage.db.chain_signals", "ChainSignalDB")

    @property
    def quality_scores(self):
        return self._lazy_store(
            "quality_scores", "pixl.storage.db.quality_scores", "QualityScoreDB"
        )

    @property
    def heartbeat_runs(self):
        return self._lazy_store(
            "heartbeat_runs", "pixl.storage.db.heartbeat_runs", "HeartbeatRunDB"
        )

    @property
    def wakeup_queue(self):
        return self._lazy_store("wakeup_queue", "pixl.storage.db.wakeup_queue", "WakeupQueueDB")

    @property
    def cost_events(self):
        return self._lazy_store("cost_events", "pixl.storage.db.cost_events", "CostEventDB")

    @property
    def task_sessions(self):
        return self._lazy_store("task_sessions", "pixl.storage.db.task_sessions", "TaskSessionDB")

    @property
    def summaries(self):
        return self._lazy_store("summaries", "pixl.storage.db.summaries", "SummaryDB")

    @property
    def sandboxes(self):
        return self._lazy_store("sandboxes", "pixl.storage.db.sandboxes", "SandboxDB")

    @property
    def workflow_templates(self):
        return self._lazy_store(
            "workflow_templates",
            "pixl.storage.db.workflow_templates",
            "WorkflowTemplateDB",
        )

    def _connect(self) -> sqlite3.Connection:
        """Create and configure SQLite connection."""
        self.pixl_dir.mkdir(parents=True, exist_ok=True)
        # Ensure .pixl directory is not group/world accessible
        if self.pixl_dir.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            self.pixl_dir.chmod(0o700)

        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )

        # Enforce restrictive permissions on the database file
        if self.db_path.exists() and self.db_path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            self.db_path.chmod(0o600)
        conn.row_factory = sqlite3.Row

        # Performance and safety pragmas
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")  # 30s — safety net for write contention
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

        return conn

    def initialize(self) -> None:
        """Create schema and run migrations.

        Safe to call multiple times. Detects current schema version
        and applies any pending migrations.
        """
        current_version = self._get_schema_version()

        if current_version == 0:
            # Fresh database - create everything
            self.conn.executescript(get_schema_sql())
            self.conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            self.conn.commit()
        elif current_version < SCHEMA_VERSION:
            # Apply incremental migrations to preserve existing data.
            self._migrate(current_version)

    def _migrate(self, from_version: int) -> None:
        """Apply incremental schema migrations to preserve data.

        Each migration block handles one version bump. The schema SQL
        (_SCHEMA_SQL) remains the source of truth for new databases;
        these migrations bring existing databases up to date.
        """
        if from_version < 33:
            # v32 → v33: tighten constraints, remove redundant indexes
            # Indexes are soft — DROP IF EXISTS is safe on live data.
            self.conn.executescript("""
                DROP INDEX IF EXISTS idx_transitions_entity_id;
                DROP INDEX IF EXISTS idx_artifact_chunks_artifact;
            """)
            # Note: CHECK constraints and FK additions only apply to new rows
            # in SQLite (ALTER TABLE cannot add constraints to existing columns).
            # The updated _SCHEMA_SQL handles new databases correctly.

        if from_version < 34:
            # v33 → v34: add execution lock columns to node_instances
            self.conn.executescript("""
                ALTER TABLE node_instances ADD COLUMN execution_run_id TEXT;
                ALTER TABLE node_instances ADD COLUMN execution_locked_at TEXT;
            """)

        if from_version < 35:
            # v34 → v35: add sandbox project tracking tables
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sandbox_projects (
                id              TEXT PRIMARY KEY,
                sandbox_url     TEXT NOT NULL,
                repo_url        TEXT,
                branch          TEXT NOT NULL DEFAULT 'main',
                status          TEXT NOT NULL DEFAULT 'creating'
                    CHECK (status IN (
                        'creating','ready','running',
                        'stopped','error','destroyed'
                    )),
                pixl_version    TEXT,
                claude_version  TEXT,
                env_keys_json   TEXT NOT NULL DEFAULT '[]',
                config_json     TEXT NOT NULL DEFAULT '{}',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT,
                destroyed_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS sandbox_operations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  TEXT NOT NULL
                    REFERENCES sandbox_projects(id) ON DELETE CASCADE,
                operation   TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'started'
                    CHECK (status IN ('started','completed','failed')),
                duration_ms     INTEGER,
                request_json    TEXT,
                response_json   TEXT,
                error           TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_sandbox_ops_project
                ON sandbox_operations(project_id);
            CREATE INDEX IF NOT EXISTS idx_sandbox_ops_created
                ON sandbox_operations(created_at);
            """)

        if from_version < 36:
            # v35 → v36: add sandbox provenance columns for data sync (GAP-10)
            self.conn.executescript("""
                ALTER TABLE events ADD COLUMN sandbox_origin_id TEXT;
                ALTER TABLE workflow_sessions ADD COLUMN sandbox_origin_id TEXT;
                ALTER TABLE artifacts ADD COLUMN sandbox_origin_id TEXT;
            """)

        if from_version < 37:
            # v36 → v37: add DB-backed workflow templates with versioning
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    description TEXT,
                    version     INTEGER NOT NULL DEFAULT 1,
                    yaml_content TEXT NOT NULL,
                    config_json  TEXT NOT NULL DEFAULT '{}',
                    source       TEXT NOT NULL DEFAULT 'db'
                        CHECK (source IN ('db', 'filesystem', 'imported')),
                    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at   TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_wf_templates_name ON workflow_templates(name);
            """)

        self.conn.execute(
            "INSERT OR REPLACE INTO schema_version (version, migrated_at) "
            "VALUES (?, datetime('now'))",
            (SCHEMA_VERSION,),
        )
        self.conn.commit()

    def _get_schema_version(self) -> int:
        """Get current schema version, 0 if no schema exists."""
        try:
            row = self.conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ).fetchone()
            return row["version"] if row else 0
        except sqlite3.OperationalError:
            return 0

    # Config helpers (key-value store in the `config` table)

    def get_config(self, key: str, default: str | None = None) -> str | None:
        """Read a value from the config table.

        Returns *default* when the key does not exist.
        """
        row = self.conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_config(self, key: str, value: str) -> None:
        """Upsert a value into the config table."""
        self.conn.execute(
            """INSERT OR REPLACE INTO config (key, value, updated_at)
               VALUES (?, ?, datetime('now'))""",
            (key, value),
        )
        self.conn.commit()

    def close(self) -> None:
        """Close database connection for the current thread.

        Note: This only closes the calling thread's connection.
        Other threads with thread-local connections will have their
        connections closed when those threads exit.
        """
        if self._thread_local.conn is not None:
            with contextlib.suppress(sqlite3.ProgrammingError):
                self._thread_local.conn.close()
            self._thread_local.conn = None
        # DO NOT reset store references — they are shared across threads
        # and delegate to thread-local connections via self._db.conn.
        # Nullifying them here races with other threads mid-request.

    def __enter__(self) -> "PixlDB":
        self.initialize()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
