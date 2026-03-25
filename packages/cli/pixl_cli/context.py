"""CLI context resolution — project detection, storage initialization.

Every CLI command receives a CLIContext via Click's `pass_context`.
The context resolves the project from cwd or --project flag,
initializes engine storage, and reads env vars set by the
orchestrator during workflow execution.
"""

from __future__ import annotations

import os
from pathlib import Path

from pixl.paths import canonical_project_root, get_db_dir, get_project_id
from pixl.storage import create_storage
from pixl.storage.protocols import StorageBackend


class CLIContext:
    """Resolved project context for CLI commands.

    Attributes:
        project_path: Canonical project root directory.
        project_id: Stable project identifier (name-hash).
        pixl_dir: Path to the .pixl metadata directory.
        db: StorageBackend instance (lazy-initialized).
        session_id: Current workflow session (from env, if any).
        stage_id: Current DAG node (from env, if any).
        is_json: Whether to emit JSON output.
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        is_json: bool = False,
    ) -> None:
        # Resolve project path from flag, env, or cwd
        if project:
            self.project_path = canonical_project_root(Path(project).resolve())
        elif env_project := os.getenv("PIXL_STORAGE_PROJECT"):
            # Inside a workflow — use the orchestrator's project override
            from pixl.paths import get_global_pixl_dir

            self.project_path = get_global_pixl_dir() / "projects" / env_project
        else:
            self.project_path = canonical_project_root(Path.cwd())

        self.project_id = get_project_id(self.project_path)
        self.pixl_dir = get_db_dir(self.project_path)
        self.is_json = is_json

        # Workflow context from env vars (set by OrchestratorCore._stage_env_context)
        self.session_id: str | None = os.getenv("PIXL_SESSION_ID")
        self.stage_id: str | None = os.getenv("PIXL_STAGE_ID")

        # Lazy storage
        self._db: StorageBackend | None = None

    @property
    def db(self) -> StorageBackend:
        """Get or create the storage backend (lazy)."""
        if self._db is None:
            self._db = create_storage(self.project_path)
        return self._db

    def ensure_session(self) -> str:
        """Ensure a session exists for CLI artifact operations.

        If PIXL_SESSION_ID is set (inside a workflow), returns it.
        Otherwise creates a one-time CLI feature + session and caches the ID.
        """
        if self.session_id:
            return self.session_id

        # Check for existing CLI session
        latest = self.db.sessions.get_latest_session(feature_id="cli-manual")
        if latest:
            self.session_id = latest["id"]
            return str(self.session_id)

        # Create a CLI feature and session
        feature = self.db.backlog.add_feature(
            title="CLI Manual Operations",
            feature_type="feature",
            status="in_progress",
        )
        session = self.db.sessions.create_session(
            feature_id=feature["id"],
            snapshot_hash="cli-manual",
        )
        self.session_id = session["id"]
        return str(self.session_id)

    def close(self) -> None:
        """Close storage if it was initialized."""
        if self._db is not None:
            self._db.close()
            self._db = None
