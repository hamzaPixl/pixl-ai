"""Process-global per-project PixlDB singleton registry.

Ensures that all code paths within the same process share a single
``PixlDB`` instance (and therefore a single family of thread-local
SQLite connections) per project.  This eliminates duplicate connection
handles that compete for SQLite's single-writer lock.

Usage::

    from pixl.storage.db.db_registry import get_project_db

    db = get_project_db(project_path)
    db.backlog.list_features()
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_registry: dict[str, PixlDB] = {}  # keyed by resolved path string


def get_project_db(
    project_path: Path,
    *,
    pixl_dir: Path | None = None,
) -> PixlDB:
    """Get or create the singleton ``PixlDB`` for *project_path*.

    Thread-safe via double-checked locking.  The ``PixlDB`` itself
    uses thread-local connections internally, so concurrent access
    from multiple threads is safe.

    Args:
        project_path: Root directory of the Pixl project.
        pixl_dir: Optional override for the ``.pixl`` metadata directory.
                  Only used when creating the instance for the first time;
                  subsequent calls with a different *pixl_dir* for the same
                  resolved path are silently ignored.
    """
    key = str(project_path.resolve())

    # Fast path – no lock needed for the common case.
    db = _registry.get(key)
    if db is not None:
        return db

    # Slow path – create under lock (double-checked).
    with _lock:
        db = _registry.get(key)
        if db is not None:
            return db

        from pixl.storage.db.connection import PixlDB

        db = PixlDB(project_path, pixl_dir=pixl_dir)
        db.initialize()
        _registry[key] = db
        logger.debug("Registered PixlDB for %s", key)
        return db


def close_project_db(project_path: Path) -> None:
    """Close and remove the ``PixlDB`` for *project_path*."""
    key = str(project_path.resolve())
    with _lock:
        db = _registry.pop(key, None)
    if db is not None:
        db.close()
        logger.debug("Closed PixlDB for %s", key)


def close_all() -> None:
    """Close every registered ``PixlDB`` (call on process shutdown)."""
    with _lock:
        for key, db in list(_registry.items()):
            try:
                db.close()
            except Exception:
                logger.warning("Error closing PixlDB for %s", key, exc_info=True)
        _registry.clear()
    logger.debug("All PixlDB instances closed")


def _reset_for_testing() -> None:
    """Clear the registry without closing connections (test isolation)."""
    with _lock:
        _registry.clear()
