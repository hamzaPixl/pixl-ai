"""Pixl storage layer.

Two storage backends are available:
1. SQLite with FTS5 — via create_storage() factory or BacklogStore adapter
2. JSON file-based — WorkflowSessionStore

For existing callers that depend on BacklogStore returning Pydantic models:

    from pixl.storage import BacklogStore
    store = BacklogStore(project_path)
    feature = store.get_feature("feat-001")  # Returns Feature model

For new code using the protocol-based API:

    from pixl.storage import create_storage
    from pixl.storage.protocols import StorageBackend

    db: StorageBackend = create_storage(project_path)
    db.backlog.add_feature(...)
"""

from pathlib import Path

# Session management
from pixl.session import SessionManager, SessionMutationError

# SQLite-backed adapter with Pydantic model API (drop-in replacement)
from pixl.storage.backlog_adapter import BacklogStoreAdapter as BacklogStore
from pixl.storage.boulder_store import BoulderStore
from pixl.storage.config_store import ConfigStore

# Protocol interfaces (callers should type-hint against these)
from pixl.storage.protocols import (
    ArtifactStore,
    EventStore,
    KnowledgeStore,
    SessionStore,
    StorageBackend,
)
from pixl.storage.protocols import (
    BacklogStore as BacklogStoreProtocol,
)

# Usage limits storage
from pixl.storage.usage_limits_store import UsageLimitsStore

# Workflow storage
from pixl.storage.workflow_session_store import WorkflowSessionStore
from pixl.storage.workflow_store import WorkflowStore


def create_storage(project_path: Path, backend: str = "sqlite") -> StorageBackend:
    """Factory: create a storage backend for a project.

    This is the single entry point for obtaining a storage instance.
    Callers should depend on the StorageBackend protocol, not on
    any concrete implementation.

    To swap backends in the future, add a new backend option here.
    All callers remain unchanged.

    Args:
        project_path: Root directory of the project.
        backend: Storage backend to use. Currently only "sqlite".

    Returns:
        A StorageBackend instance, initialized and ready to use.

    Raises:
        ValueError: If backend is not recognized.
    """
    if backend == "sqlite":
        from pixl.storage.db.db_registry import get_project_db

        return get_project_db(project_path)
    else:
        raise ValueError(f"Unknown storage backend: {backend!r}. Available: 'sqlite'")


__all__ = [
    # Adapter (Pydantic model API backed by SQLite)
    "BacklogStore",
    # Factory
    "create_storage",
    # Protocols (for type hints)
    "StorageBackend",
    "BacklogStoreProtocol",
    "KnowledgeStore",
    "ArtifactStore",
    "EventStore",
    "SessionStore",
    # Additional stores
    "BoulderStore",
    "ConfigStore",
    "WorkflowSessionStore",
    "WorkflowStore",
    "UsageLimitsStore",
    "SessionManager",
    "SessionMutationError",
]
