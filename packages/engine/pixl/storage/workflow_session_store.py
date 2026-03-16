"""Workflow session storage.

Manages persistence of workflow sessions with SQLite as the
authoritative store.  Session directories under
``.pixl/sessions/sess-XXXX/`` are retained only for artifact
file caching.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from pixl.errors import StateError, StorageError
from pixl.models.event import Event
from pixl.models.session import WorkflowSession
from pixl.models.workflow import WorkflowSnapshot
from pixl.paths import get_sessions_dir

if TYPE_CHECKING:
    from pixl.models.event import EventType
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)

class WorkflowSessionStore:
    """Manages workflow session persistence with atomic writes and event logging."""

    def __init__(self, project_path: Path, db: PixlDB | None = None) -> None:
        """Initialize the store.

        Args:
            project_path: Path to the project root
            db: Optional pre-initialized PixlDB to reuse (avoids duplicate DB handles)
        """
        self.project_path = project_path
        self.sessions_dir = get_sessions_dir(project_path)
        self._db = db  # Lazy-initialized PixlDB when not provided

    def touch_session(self, session_id: str) -> bool:
        """Lightweight heartbeat — only updates last_updated_at.

        Called periodically by the executor to prevent zombie detection.
        """
        try:
            db = self._get_db()
            return db.sessions.touch_session(session_id)
        except Exception:
            logger.debug("Session heartbeat touch failed for %s", session_id, exc_info=True)
            return False

    def mark_session_started(self, session_id: str) -> bool:
        """Mark session started once (idempotent)."""
        try:
            db = self._get_db()
            row = db.conn.execute(
                "SELECT started_at FROM workflow_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row and row["started_at"]:
                return False
            return db.sessions.update_session(
                session_id,
                started_at=datetime.now().isoformat(),
            )
        except Exception:
            logger.warning("Failed to mark session %s as started", session_id, exc_info=True)
            return False

    def mark_session_ended(self, session_id: str) -> bool:
        """Mark session ended (and backfill started_at if missing)."""
        try:
            db = self._get_db()
            now = datetime.now().isoformat()
            row = db.conn.execute(
                "SELECT started_at FROM workflow_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            updates: dict[str, Any] = {"ended_at": now}
            if not row or not row["started_at"]:
                updates["started_at"] = now
            return db.sessions.update_session(session_id, **updates)
        except Exception:
            logger.warning("Failed to mark session %s as ended", session_id, exc_info=True)
            return False

    def persist_artifact_record(
        self,
        *,
        name: str,
        artifact_type: str,
        task_id: str,
        session_id: str,
        content: str,
        path: str | None,
        feature_id: str | None,
        epic_id: str | None,
        tags: list[str] | None,
        extra: dict[str, Any] | None,
    ) -> None:
        """Persist artifact metadata/content into DB search store (upsert)."""
        db = self._get_db()
        self._ensure_session_row(session_id)
        logical_path = path or name
        existing = db.artifacts.get_by_session_path(session_id, logical_path)
        if existing:
            db.artifacts.update(
                existing["id"],
                content=content,
                type=artifact_type,
                task_id=task_id,
                tags=tags,
                extra=extra,
            )
        else:
            db.artifacts.put(
                session_id=session_id,
                logical_path=logical_path,
                content=content,
                artifact_type=artifact_type,
                task_id=task_id,
                name=name,
                feature_id=feature_id,
                epic_id=epic_id,
                tags=tags,
                extra=extra,
            )

    def _ensure_sessions_dir(self) -> None:
        """Ensure sessions directory exists."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_db(self):
        """Lazy-initialize the SQLite backend (PixlDB) via the singleton registry."""
        if self._db is None:
            from pixl.storage.db.db_registry import get_project_db

            self._db = get_project_db(self.project_path)
        return self._db

    def _ensure_session_row(self, session_id: str) -> None:
        """Ensure a workflow session row exists for artifact FK integrity.

        Some execution and test paths write artifacts before the session has
        been explicitly persisted. In DB-canonical mode we still need those
        writes to succeed, so create a minimal placeholder session row.
        """
        db = self._get_db()
        if db.sessions.get_session(session_id) is not None:
            return

        now = datetime.now().isoformat()
        db.conn.execute(
            """INSERT OR IGNORE INTO workflow_sessions
               (id, snapshot_hash, created_at, last_updated_at)
               VALUES (?, ?, ?, ?)""",
            (session_id, f"adhoc-{session_id}", now, now),
        )
        db.conn.commit()

    def _ensure_feature_exists(self, feature_id: str) -> None:
        """Ensure a feature exists for FK integrity (best-effort).

        Creates a minimal placeholder when the feature ID matches the
        default pattern and is missing. This keeps SQLite workflows
        usable in tests and flows that don't pre-create features.
        """
        import re
        from datetime import datetime

        db = self._get_db()
        if db.backlog.get_feature(feature_id):
            return

        now = datetime.now().isoformat()
        db.conn.execute(
            """INSERT OR IGNORE INTO features
               (id, title, description, type, priority, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                feature_id,
                f"Auto-created {feature_id}",
                "",
                "chore",
                "P2",
                "backlog",
                now,
            ),
        )

        # Bump id sequence if needed to avoid collisions
        match = re.match(r"^feat-(\d{3})$", feature_id)
        if match:
            num = int(match.group(1))
            db.conn.execute(
                """UPDATE id_sequences
                   SET next_value = CASE
                       WHEN next_value <= ? THEN ?
                       ELSE next_value
                   END
                   WHERE name = 'feature'""",
                (num, num + 1),
            )
        db.conn.commit()

    def _session_from_db(self, data: dict[str, Any]) -> WorkflowSession:
        """Convert a DB session dict into a WorkflowSession model."""
        session_data: dict[str, Any] = {
            "session_schema_version": data.get("schema_version", 1),
            "id": data["id"],
            "feature_id": data.get("feature_id") or "",
            "snapshot_hash": data.get("snapshot_hash") or "",
            "created_at": data.get("created_at"),
            "started_at": data.get("started_at"),
            "ended_at": data.get("ended_at"),
            "last_updated_at": data.get("last_updated_at"),
            "node_instances": data.get("node_instances", {}),
            "loop_state": data.get("loop_state", {}),
            "executor_cursor": data.get("cursor"),
            "baseline_commit": data.get("baseline_commit"),
            "workspace_root": data.get("workspace_root"),
            "frozen_artifacts": data.get("frozen_artifacts", {}),
            "artifacts": data.get("artifacts", []),
            "structured_outputs": data.get("structured_outputs", {}),
            "session_state": data.get("session_state", {}),
            "paused_at": data.get("paused_at"),
            "pause_reason": data.get("pause_reason"),
            "baton": data.get("baton"),
            "baton_history": data.get("baton_history", []),
            "context_audit": data.get("context_audit", []),
        }
        return WorkflowSession.model_validate(session_data)

    def _merge_file_session_runtime(
        self,
        *,
        session: WorkflowSession,
        file_session: WorkflowSession,
    ) -> None:
        """Merge runtime fields from session.json for backward compatibility.

        DB is authoritative for core execution state; file data only fills
        fields not yet represented in older DB schemas.
        """
        if file_session.artifacts:
            session.artifacts = file_session.artifacts

        if not session.structured_outputs and file_session.structured_outputs:
            session.structured_outputs = file_session.structured_outputs
        if not session.session_state and file_session.session_state:
            session.session_state = file_session.session_state
        if session.baton is None and file_session.baton is not None:
            session.baton = file_session.baton
        if not session.baton_history and file_session.baton_history:
            session.baton_history = file_session.baton_history
        if not session.context_audit and file_session.context_audit:
            session.context_audit = file_session.context_audit

        for node_id, file_instance in file_session.node_instances.items():
            instance = session.node_instances.get(node_id)
            if instance is None:
                session.node_instances[node_id] = dict(file_instance)
                continue
            for key, value in file_instance.items():
                if key not in instance or instance[key] is None:
                    instance[key] = value

    def _session_dir(self, session_id: str) -> Path:
        """Get path for a session directory."""
        return self.sessions_dir / session_id

    def _artifacts_dir(self, session_id: str) -> Path:
        """Get path for artifacts directory."""
        return self._session_dir(session_id) / "artifacts"

    def _normalize_artifact_name(self, artifact_name: str) -> str:
        """Normalize and validate session-scoped artifact paths."""
        raw = (artifact_name or "").strip().replace("\\", "/")
        # Strip sessions/<id>/artifacts/ prefix (agents may use full session path)
        _sessions_prefix = re.match(r"^sessions/[^/]+/artifacts/(.+)$", raw)
        if _sessions_prefix:
            raw = _sessions_prefix.group(1)
        if raw.startswith("artifacts/"):
            raw = raw[len("artifacts/") :]
        if raw.startswith("/"):
            abs_parts = list(PurePosixPath(raw).parts)
            if "artifacts" in abs_parts:
                idx = abs_parts.index("artifacts")
                raw = "/".join(abs_parts[idx + 1 :])
        if not raw:
            raise StorageError(
                "Artifact name cannot be empty",
                op="normalize_artifact_name",
                metadata={"artifact_name": artifact_name},
            )
        candidate = PurePosixPath(raw)
        if candidate.is_absolute():
            raise StorageError(
                "Artifact path must be relative to session scope",
                op="normalize_artifact_name",
                metadata={"artifact_name": artifact_name},
            )
        parts: list[str] = []
        for part in candidate.parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise StorageError(
                    "Artifact path traversal is not allowed",
                    op="normalize_artifact_name",
                    metadata={"artifact_name": artifact_name},
                )
            parts.append(part)
        if not parts:
            raise StorageError(
                "Artifact path must contain at least one segment",
                op="normalize_artifact_name",
                metadata={"artifact_name": artifact_name},
            )
        return "/".join(parts)

    def _session_file(self, session_id: str) -> Path:
        """Get path for session.json."""
        return self._session_dir(session_id) / "session.json"

    def _snapshot_file(self, session_id: str) -> Path:
        """Get path for snapshot.json."""
        return self._session_dir(session_id) / "snapshot.json"

    def _ensure_session_row_in_db(
        self,
        conn,
        *,
        session_id: str,
        feature_id: str | None = None,
        snapshot_hash: str | None = None,
        created_at: str | None = None,
        last_updated_at: str | None = None,
        baseline_commit: str | None = None,
        workspace_root: str | None = None,
    ) -> None:
        """Ensure the workflow_sessions FK parent row exists."""
        existing = conn.execute(
            "SELECT 1 FROM workflow_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if existing:
            return

        # Best-effort hydration from session.json when caller only has session_id.
        if not any((feature_id, snapshot_hash, created_at, baseline_commit, workspace_root)):
            session_file = self._session_file(session_id)
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text(encoding="utf-8"))
                    feature_id = feature_id or data.get("feature_id")
                    snapshot_hash = snapshot_hash or data.get("snapshot_hash")
                    created_at = created_at or data.get("created_at")
                    baseline_commit = baseline_commit or data.get("baseline_commit")
                    workspace_root = workspace_root or data.get("workspace_root")
                except Exception:
                    logger.debug(
                        "Failed to read session file for defaults: %s", session_id, exc_info=True
                    )

        now_iso = datetime.now().isoformat()
        created_at = created_at or now_iso
        last_updated_at = last_updated_at or now_iso
        feature_id = feature_id or None
        snapshot_hash = snapshot_hash or ""

        if feature_id:
            conn.execute(
                """INSERT OR IGNORE INTO features
                   (id, title, description, type, priority, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    feature_id,
                    f"Auto-created {feature_id}",
                    "",
                    "chore",
                    "P2",
                    "backlog",
                    created_at,
                ),
            )

        conn.execute(
            """INSERT OR IGNORE INTO workflow_sessions
               (id, feature_id, snapshot_hash, created_at, last_updated_at,
                baseline_commit, workspace_root)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                feature_id,
                snapshot_hash,
                created_at,
                last_updated_at,
                baseline_commit,
                workspace_root,
            ),
        )

    # Session CRUD

    def create_session(
        self,
        feature_id: str,
        snapshot: WorkflowSnapshot,
    ) -> WorkflowSession:
        """Create a new workflow session.

        Args:
            feature_id: Associated feature ID
            snapshot: WorkflowSnapshot to execute

        Returns:
            Created WorkflowSession
        """
        self._ensure_feature_exists(feature_id)

        # Capture git baseline for contract validation
        baseline_commit, workspace_root = WorkflowSession._capture_git_baseline(self.project_path)

        db = self._get_db()
        db.sessions.save_snapshot(snapshot.snapshot_hash, snapshot.model_dump_json())

        db_session = db.sessions.create_session(
            feature_id=feature_id,
            snapshot_hash=snapshot.snapshot_hash,
            baseline_commit=baseline_commit,
            workspace_root=workspace_root,
        )
        session = self._session_from_db(db_session)

        session_dir = self._session_dir(session.id)
        session_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts_dir(session.id).mkdir(exist_ok=True)

        self.append_event(
            Event.session_created(
                session.id,
                data={
                    "feature_id": feature_id,
                    "snapshot_hash": snapshot.snapshot_hash,
                },
            ),
            session.id,
        )

        return session

    def load_session(self, session_id: str) -> WorkflowSession | None:
        """Load a session from SQLite.

        Args:
            session_id: Session ID to load

        Returns:
            WorkflowSession or None if not found
        """
        # Prefer SQLite session if available
        try:
            db = self._get_db()
            db_session = db.sessions.get_session(session_id)
            if db_session:
                session = self._session_from_db(db_session)
                return session
        except Exception as exc:
            # DB unavailable — log and return None
            self._record_storage_error(
                session_id,
                "load_session_db",
                {"error": str(exc)},
                exc,
            )

        return None

    def get_session(self, session_id: str) -> WorkflowSession | None:
        """Backward-compatible alias for load_session()."""
        return self.load_session(session_id)

    def save_session(self, session: WorkflowSession) -> None:
        """Save session to SQLite (authoritative).

        Args:
            session: Session to save
        """
        try:
            db = self._get_db()
            self._persist_session_to_db(db.conn, session)
            db.conn.commit()
        except Exception as exc:
            raise StorageError(
                "Failed to save session",
                op="save_session",
                details=str(exc),
                metadata={"session_id": session.id},
                cause=exc,
            ) from exc

    def _persist_session_to_db(self, conn, session: WorkflowSession) -> None:
        """Persist session state to SQLite using the provided connection."""
        last_updated_at = session.last_updated_at or datetime.now()
        session.last_updated_at = last_updated_at
        created_at = (
            session.created_at.isoformat() if session.created_at else last_updated_at.isoformat()
        )
        self._ensure_session_row_in_db(
            conn,
            session_id=session.id,
            feature_id=session.feature_id,
            snapshot_hash=session.snapshot_hash,
            created_at=created_at,
            last_updated_at=last_updated_at.isoformat(),
            baseline_commit=session.baseline_commit,
            workspace_root=session.workspace_root,
        )

        cursor_json = (
            json.dumps(session.executor_cursor.to_dict()) if session.executor_cursor else None
        )
        frozen_json = json.dumps(session.frozen_artifacts or {})
        structured_outputs_json = json.dumps(session.structured_outputs or {})
        session_state_json = json.dumps(session.session_state or {})
        baton_json = json.dumps(session.baton) if session.baton else None
        baton_history_json = json.dumps(session.baton_history or [])
        context_audit_json = json.dumps(session.context_audit or [])

        conn.execute(
            """UPDATE workflow_sessions
               SET snapshot_hash = ?,
                   started_at = ?,
                   ended_at = ?,
                   last_updated_at = ?,
                   baseline_commit = ?,
                   workspace_root = ?,
                   cursor_json = ?,
                   frozen_artifacts = ?,
                   structured_outputs_json = ?,
                   session_state_json = ?,
                   paused_at = ?,
                   pause_reason = ?,
                   baton_json = ?,
                   baton_history_json = ?,
                   context_audit_json = ?
               WHERE id = ?""",
            (
                session.snapshot_hash,
                session.started_at.isoformat() if session.started_at else None,
                session.ended_at.isoformat() if session.ended_at else None,
                last_updated_at.isoformat(),
                session.baseline_commit,
                session.workspace_root,
                cursor_json,
                frozen_json,
                structured_outputs_json,
                session_state_json,
                session.paused_at.isoformat() if session.paused_at else None,
                session.pause_reason,
                baton_json,
                baton_history_json,
                context_audit_json,
                session.id,
            ),
        )

        for node_id, instance in session.node_instances.items():
            output = instance.get("output")
            output_json = json.dumps(output) if output is not None else None
            base_keys = {
                "node_id",
                "state",
                "attempt",
                "ready_at",
                "started_at",
                "ended_at",
                "blocked_reason",
                "output",
                "failure_kind",
                "error_message",
                "model_name",
                "agent_name",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cost_usd",
            }
            metadata = {k: v for k, v in instance.items() if k not in base_keys}
            metadata_json = json.dumps(metadata) if metadata else "{}"
            conn.execute(
                """INSERT INTO node_instances
                   (session_id, node_id, state, attempt, ready_at, started_at, ended_at,
                    blocked_reason, output_json, failure_kind, error_message,
                    model_name, agent_name,
                    input_tokens, output_tokens, total_tokens, cost_usd,
                    metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(session_id, node_id) DO UPDATE SET
                     state = excluded.state,
                     attempt = excluded.attempt,
                     ready_at = excluded.ready_at,
                     started_at = excluded.started_at,
                     ended_at = excluded.ended_at,
                     blocked_reason = excluded.blocked_reason,
                     output_json = excluded.output_json,
                     failure_kind = excluded.failure_kind,
                     error_message = excluded.error_message,
                     model_name = COALESCE(excluded.model_name, node_instances.model_name),
                     agent_name = COALESCE(excluded.agent_name, node_instances.agent_name),
                     input_tokens = excluded.input_tokens,
                     output_tokens = excluded.output_tokens,
                     total_tokens = excluded.total_tokens,
                     cost_usd = excluded.cost_usd,
                     metadata_json = excluded.metadata_json""",
                (
                    session.id,
                    node_id,
                    instance.get("state", ""),
                    instance.get("attempt", 0),
                    instance.get("ready_at"),
                    instance.get("started_at"),
                    instance.get("ended_at"),
                    instance.get("blocked_reason"),
                    output_json,
                    instance.get("failure_kind"),
                    instance.get("error_message"),
                    instance.get("model_name"),
                    instance.get("agent_name"),
                    instance.get("input_tokens", 0),
                    instance.get("output_tokens", 0),
                    instance.get("total_tokens", 0),
                    instance.get("cost_usd", 0.0),
                    metadata_json,
                ),
            )

        for loop_id, loop_state in session.loop_state.items():
            history_json = json.dumps(loop_state.get("history", []))
            conn.execute(
                """INSERT INTO loop_states
                   (session_id, loop_id, current_iteration, max_iterations, history_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(session_id, loop_id) DO UPDATE SET
                     current_iteration = excluded.current_iteration,
                     max_iterations = excluded.max_iterations,
                     history_json = excluded.history_json""",
                (
                    session.id,
                    loop_id,
                    loop_state.get("current_iteration", 0),
                    loop_state.get("max_iterations", 3),
                    history_json,
                ),
            )

    def _record_storage_error(
        self,
        session_id: str,
        op: str,
        details: dict[str, Any] | str,
        exc: Exception | None = None,
    ) -> None:
        """Best-effort logging for storage failures."""
        logger.warning(
            "Storage error: session=%s op=%s details=%s",
            session_id,
            op,
            details,
            exc_info=exc,
        )

    # Snapshot Management

    def load_snapshot(self, session_id: str) -> WorkflowSnapshot | None:
        """Load the snapshot for a session.

        Args:
            session_id: Session ID

        Returns:
            WorkflowSnapshot or None if not found
        """
        # Prefer SQLite snapshot if available
        try:
            db = self._get_db()
            session = db.sessions.get_session(session_id)
            if session and session.get("snapshot_hash"):
                snapshot_json = db.sessions.get_snapshot(session["snapshot_hash"])
                if snapshot_json:
                    data = json.loads(snapshot_json)
                    return WorkflowSnapshot.model_validate(data)
        except Exception as exc:
            self._record_storage_error(
                session_id,
                "load_snapshot_db",
                {"error": str(exc)},
                exc,
            )
        return None

    # Event Logging

    def commit_transition(
        self,
        session: WorkflowSession,
        *,
        node_id: str | None,
        from_state: str | None,
        to_state: str | None,
        event_type: EventType,
        payload: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> Event:
        """Atomically commit an event + session state update."""
        from pixl.models.event import EventType

        if not isinstance(event_type, EventType):
            raise StateError(
                f"Invalid event type: {event_type!r}",
                invariant="event_type",
                details=str(event_type),
            )

        if node_id and to_state is not None:
            instance = session.get_node_instance(node_id)
            if not instance or instance.get("state") != to_state:
                raise StateError(
                    "Session state does not match requested transition",
                    invariant="node_state_mismatch",
                    details=f"{node_id} expected {to_state}, got {instance.get('state') if instance else None}",
                )

        event = Event.create(
            event_type,
            session.id,
            node_id=node_id,
            data=payload or {},
        )
        if timestamp:
            event.timestamp = timestamp

        if session.executor_cursor:
            session.executor_cursor.last_event_id = event.id

        conn = None
        db_error: Exception | None = None
        try:
            db = self._get_db()
            with db.write() as conn:
                conn.execute("BEGIN IMMEDIATE")
                # Persist session row/state first so event FK constraints are satisfied
                # even for sessions created outside WorkflowSessionStore.create_session().
                self._persist_session_to_db(conn, session)
                payload_json = json.dumps(event.data) if event.data else None
                conn.execute(
                    """INSERT INTO events
                       (session_id, event_type, node_id, payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        session.id,
                        event.type.value,
                        node_id,
                        payload_json,
                        event.timestamp.isoformat(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            db_error = exc
            if conn is not None:
                try:
                    conn.rollback()
                except Exception as rollback_exc:
                    _ = rollback_exc

        if db_error:
            raise StorageError(
                "Failed to commit transition",
                op="commit_transition_db",
                details=str(db_error),
                metadata={"session_id": session.id, "node_id": node_id},
                cause=db_error,
            )

        return event

    def append_event(self, event: Event, session_id: str | None = None) -> None:
        """Append event to the event log (SQLite-backed).

        Args:
            event: Event to log
            session_id: Session ID (uses event.session_id if None)
        """
        session_id = session_id or event.session_id

        try:
            db = self._get_db()
            self._ensure_session_row_in_db(
                db.conn,
                session_id=session_id,
            )
            payload = dict(event.data)
            if event.artifact_id:
                payload["artifact_id"] = event.artifact_id
            db.events.emit(
                event_type=event.type.value,
                session_id=session_id,
                node_id=event.node_id,
                payload=payload or None,
                created_at=event.timestamp.isoformat() if event.timestamp else None,
            )
        except Exception as exc:
            raise StorageError(
                "Failed to append event",
                op="append_event",
                details=str(exc),
                metadata={"session_id": session_id, "event_type": event.type.value},
                cause=exc,
            ) from exc

    def append_events_batch(self, events: list[Event], session_id: str | None = None) -> None:
        """Append multiple events in a single DB transaction.

        More efficient than calling append_event() per event, especially for
        the 3-6 events generated per executor step.

        Args:
            events: Events to log
            session_id: Session ID override (uses event.session_id if None)
        """
        if not events:
            return

        resolved_session_id = session_id or events[0].session_id

        try:
            db = self._get_db()
            self._ensure_session_row_in_db(db.conn, session_id=resolved_session_id)
            with db.events.batch():
                for event in events:
                    payload = dict(event.data)
                    if event.artifact_id:
                        payload["artifact_id"] = event.artifact_id
                    db.events.emit(
                        event_type=event.type.value,
                        session_id=session_id or event.session_id,
                        node_id=event.node_id,
                        payload=payload or None,
                        created_at=event.timestamp.isoformat() if event.timestamp else None,
                    )
        except Exception as exc:
            raise StorageError(
                "Failed to batch append events",
                op="append_events_batch",
                details=str(exc),
                metadata={"session_id": resolved_session_id, "count": len(events)},
                cause=exc,
            ) from exc

    def load_events(self, session_id: str, limit: int | None = None) -> list[Event]:
        """Load events from SQLite.

        Args:
            session_id: Session ID
            limit: Maximum number of events to load (None = all)

        Returns:
            List of Events
        """
        db = self._get_db()
        rows = db.events.get_events(
            session_id=session_id,
            limit=limit,
        )
        events = []
        for row in rows:
            event = self._event_from_db_row(row)
            events.append(event)
        return events

    @staticmethod
    def _event_from_db_row(row: dict) -> Event:
        """Convert a DB event row dict to an Event model instance."""
        from pixl.models.event import EventType

        event_type_str = row.get("event_type", "error")
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.ERROR

        data: dict = {}
        if row.get("payload"):
            if isinstance(row["payload"], dict):
                data = row["payload"]
            elif isinstance(row["payload"], str):
                data = json.loads(row["payload"])

        timestamp = datetime.now()
        if row.get("created_at"):
            with contextlib.suppress(ValueError, TypeError):
                timestamp = datetime.fromisoformat(row["created_at"])

        return Event(
            id=f"evt-db-{row.get('id', 0)}",
            type=event_type,
            timestamp=timestamp,
            session_id=row.get("session_id", ""),
            node_id=row.get("node_id"),
            data=data,
        )

    # Artifact Management

    def _write_artifact_cache_file(self, session_id: str, artifact_name: str, content: str) -> Path:
        """Write compatibility artifact file under sessions/<id>/artifacts."""
        artifact_path = self._artifacts_dir(session_id) / artifact_name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
        return artifact_path

    def save_artifact(
        self,
        session_id: str,
        artifact_name: str,
        content: str,
    ) -> dict[str, Any]:
        """Save an artifact file.

        Args:
            session_id: Session ID
            artifact_name: Artifact filename
            content: File content

        Returns:
            Dict with ``path`` (Path) and ``content_hash`` (str, SHA256 hex).
        """
        normalized = self._normalize_artifact_name(artifact_name)
        # Compatibility path construction (no write)
        artifact_path = self._artifacts_dir(session_id) / normalized

        # DB-canonical write (session-scoped); file write above is compatibility cache.
        db = self._get_db()
        self._ensure_session_row(session_id)
        session_row = db.sessions.get_session(session_id)
        feature_id = session_row.get("feature_id") if session_row else None
        epic_id = None
        if (
            feature_id
            and isinstance(feature_id, str)
            and (feature_id.startswith("epic-") or not feature_id.startswith("feat-"))
        ):
            epic_id = feature_id

        result = db.artifacts.put(
            session_id=session_id,
            logical_path=normalized,
            content=content,
            artifact_type="other",
            task_id="manual",
            name=normalized,
            feature_id=feature_id
            if isinstance(feature_id, str) and feature_id.startswith("feat-")
            else None,
            epic_id=epic_id,
        )
        content_hash = result.get("content_hash", "") if isinstance(result, dict) else ""
        return {"path": artifact_path, "content_hash": content_hash}

    def load_artifact(self, session_id: str, artifact_name: str) -> str | None:
        """Load an artifact file.

        Args:
            session_id: Session ID
            artifact_name: Artifact filename

        Returns:
            File content or None if not found
        """
        normalized = self._normalize_artifact_name(artifact_name)
        db = self._get_db()
        artifact = db.artifacts.get_by_session_path(session_id, normalized)
        if artifact is not None:
            content = artifact.get("content")
            if isinstance(content, str):
                return content

        return None

    def list_artifacts(self, session_id: str) -> list[Path]:
        """List artifacts in a session.

        Args:
            session_id: Session ID

        Returns:
            List of artifact paths
        """
        artifacts_dir = self._artifacts_dir(session_id)
        artifacts: list[Path] = []

        # DB is canonical source.
        try:
            db_rows = self._get_db().artifacts.list_page(
                session_id=session_id, limit=5000, offset=0
            )
            seen: set[str] = set()
            for row in db_rows:
                logical_path = row.get("path") or row.get("name")
                if not isinstance(logical_path, str):
                    continue
                if logical_path in seen:
                    continue
                seen.add(logical_path)
                artifacts.append(artifacts_dir / logical_path)
        except Exception:
            pass

        artifacts.sort()
        return artifacts

    # Artifact Versioning

    def save_artifact_versioned(
        self,
        session_id: str,
        artifact_name: str,
        content: str,
    ) -> tuple[Path, int]:
        """Save an artifact with version tracking.

        Each save creates a new version in the versions/ subdirectory
        and updates the current artifact file.

        Args:
            session_id: Session ID
            artifact_name: Artifact filename
            content: File content

        Returns:
            Tuple of (path to current artifact, version number)
        """

        normalized = self._normalize_artifact_name(artifact_name)
        db = self._get_db()
        self._ensure_session_row(session_id)
        existing = db.artifacts.list_versions_by_path(normalized, session_id)
        previous_version_id = existing[-1]["id"] if existing else None
        version = len(existing) + 1
        semantic_version = f"1.0.{max(version - 1, 0)}"

        db.artifacts.put(
            session_id=session_id,
            logical_path=normalized,
            content=content,
            artifact_type="other",
            task_id="versioned_write",
            name=normalized,
            version=semantic_version,
            previous_version_id=previous_version_id,
        )

        # Compatibility path construction (no write)
        current_path = self._artifacts_dir(session_id) / normalized

        return current_path, version

    def load_artifact_version(
        self,
        session_id: str,
        artifact_name: str,
        version: int,
    ) -> str | None:
        """Load a specific version of an artifact.

        Args:
            session_id: Session ID
            artifact_name: Artifact filename
            version: Version number (1-based)

        Returns:
            File content or None if version not found
        """
        normalized = self._normalize_artifact_name(artifact_name)
        versions = self._get_db().artifacts.list_versions_by_path(normalized, session_id)
        if versions and 1 <= version <= len(versions):
            target = versions[version - 1]
            content = target.get("content")
            if isinstance(content, str):
                return content
            artifact = self._get_db().artifacts.get(str(target["id"]))
            if artifact and isinstance(artifact.get("content"), str):
                return str(artifact.get("content"))

        return None

    def list_artifact_versions(
        self,
        session_id: str,
        artifact_name: str,
    ) -> list[dict]:
        """List all versions of an artifact.

        Args:
            session_id: Session ID
            artifact_name: Artifact filename

        Returns:
            List of version info dicts with keys: version, hash, size, timestamp
        """
        normalized = self._normalize_artifact_name(artifact_name)
        db_versions = self._get_db().artifacts.list_versions_by_path(normalized, session_id)
        if db_versions:
            versions: list[dict] = []
            for idx, row in enumerate(db_versions, start=1):
                created_at = row.get("created_at")
                ts = None
                if isinstance(created_at, str):
                    with contextlib.suppress(ValueError):
                        ts = datetime.fromisoformat(created_at).timestamp()
                versions.append(
                    {
                        "version": idx,
                        "hash": str(row.get("content_hash") or "")[:12],
                        "size": int(row.get("size_bytes") or 0),
                        "timestamp": ts if ts is not None else 0.0,
                    }
                )
            return versions

        return []

    def diff_artifact_versions(
        self,
        session_id: str,
        artifact_name: str,
        from_version: int,
        to_version: int | None = None,
    ) -> list[str]:
        """Generate a unified diff between two artifact versions.

        Args:
            session_id: Session ID
            artifact_name: Artifact filename
            from_version: Base version number
            to_version: Target version number (None = current)

        Returns:
            List of diff lines
        """
        import difflib

        old_content = self.load_artifact_version(session_id, artifact_name, from_version)
        if old_content is None:
            return [f"--- Version {from_version} not found"]

        if to_version is not None:
            new_content = self.load_artifact_version(session_id, artifact_name, to_version)
            new_label = f"v{to_version}"
        else:
            new_content = self.load_artifact(session_id, artifact_name)
            new_label = "current"

        if new_content is None:
            return [f"--- {new_label} not found"]

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        return list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"{artifact_name} (v{from_version})",
                tofile=f"{artifact_name} ({new_label})",
            )
        )

    # Session Listing

    def list_sessions(self) -> list[WorkflowSession]:
        """List all sessions.

        Returns:
            List of WorkflowSessions (sorted by created_at, newest first)
        """
        # Prefer SQLite if available
        try:
            db = self._get_db()
            db_sessions = db.sessions.list_sessions()
            if db_sessions:
                sessions = [self._session_from_db(s) for s in db_sessions]
                for session in sessions:
                    session_file = self._session_file(session.id)
                    if session_file.exists():
                        try:
                            data = json.loads(session_file.read_text())
                            file_session = WorkflowSession.model_validate(data)
                            self._merge_file_session_runtime(
                                session=session,
                                file_session=file_session,
                            )
                        except Exception as exc:
                            self._record_storage_error(
                                session.id,
                                "list_sessions_merge",
                                {"error": str(exc)},
                                exc,
                            )
                return sorted(sessions, key=lambda s: s.created_at, reverse=True)
        except Exception as exc:
            self._record_storage_error(
                "sess-unknown",
                "list_sessions_db",
                {"error": str(exc)},
                exc,
            )

        sessions = []
        for session_file in self.sessions_dir.glob("*/session.json"):
            with open(session_file, encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(WorkflowSession.model_validate(data))

        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def find_active_session_for_feature(self, feature_id: str) -> WorkflowSession | None:
        """Find an active (non-terminal) session for a feature.

        Returns the first session whose status is created, running, paused,
        or stalled — i.e. not completed/failed/cancelled and not yet ended.

        Args:
            feature_id: Feature ID to check

        Returns:
            Active WorkflowSession or None
        """
        from pixl.models.session import SessionStatus

        active_statuses = {
            SessionStatus.CREATED,
            SessionStatus.RUNNING,
            SessionStatus.PAUSED,
            SessionStatus.STALLED,
        }
        for session in self.get_sessions_by_feature(feature_id):
            if session.status in active_statuses and session.ended_at is None:
                return session
        return None

    def get_sessions_by_feature(self, feature_id: str) -> list[WorkflowSession]:
        """Get all sessions for a feature.

        Args:
            feature_id: Feature ID

        Returns:
            List of WorkflowSessions
        """
        return [s for s in self.list_sessions() if s.feature_id == feature_id]

    def get_latest_session(self, feature_id: str | None = None) -> WorkflowSession | None:
        """Get the most recent session.

        Args:
            feature_id: Optional feature ID filter

        Returns:
            Latest WorkflowSession or None
        """
        sessions = self.get_sessions_by_feature(feature_id) if feature_id else self.list_sessions()
        return sessions[0] if sessions else None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session directory.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        import shutil

        try:
            db = self._get_db()
            db.sessions.delete_session(session_id)
        except Exception as exc:
            self._record_storage_error(
                session_id,
                "delete_session_db",
                {"error": str(exc)},
                exc,
            )

        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return False

        shutil.rmtree(session_dir)
        return True
