"""LRU connection pool for per-project PixlDB instances.

Caches PixlDB connections by project_id with TTL-based eviction
and a configurable maximum pool size. Thread-safe via a reentrant lock.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import NamedTuple

from pixl.projects.registry import get_project
from pixl.storage.db.connection import PixlDB
from pixl.storage.db.db_registry import get_project_db

logger = logging.getLogger(__name__)

MAX_POOL_SIZE = 50
TTL_SECONDS = 300.0  # 5 minutes


class _PoolEntry(NamedTuple):
    db: PixlDB
    last_accessed: float


class ProjectDBPool:
    """Thread-safe LRU pool of PixlDB instances keyed by project_id."""

    def __init__(
        self,
        max_size: int = MAX_POOL_SIZE,
        ttl_seconds: float = TTL_SECONDS,
    ) -> None:
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._pool: OrderedDict[str, _PoolEntry] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, project_id: str) -> PixlDB:
        """Get or create a PixlDB for *project_id*. Updates LRU ordering."""
        with self._lock:
            if project_id in self._pool:
                entry = self._pool.pop(project_id)
                updated = _PoolEntry(db=entry.db, last_accessed=time.time())
                self._pool[project_id] = updated
                return updated.db

            db = self._create_db(project_id)
            self._evict_if_needed()
            self._pool[project_id] = _PoolEntry(db=db, last_accessed=time.time())
            logger.debug("Pool: created entry for project %s", project_id)
            return db

    def close_all(self) -> None:
        """Close every pooled connection. Called on shutdown."""
        with self._lock:
            for project_id in list(self._pool):
                self._close_entry(project_id)
            logger.info("Project pool closed (%d entries removed)", len(self._pool))
            self._pool.clear()

    def sweep(self) -> int:
        """Evict entries older than TTL. Returns count of evicted entries."""
        with self._lock:
            now = time.time()
            expired = [
                pid
                for pid, entry in self._pool.items()
                if (now - entry.last_accessed) > self._ttl_seconds
            ]
            for pid in expired:
                self._close_entry(pid)
            return len(expired)

    # -- internals --

    def _create_db(self, project_id: str) -> PixlDB:
        info = get_project(project_id)
        if info is None:
            raise ValueError(f"Project not found: {project_id}")

        storage_dir = info.get("storage_dir")
        if not storage_dir:
            raise ValueError(f"Project {project_id} has no storage_dir")

        sd = Path(storage_dir)
        return get_project_db(sd, pixl_dir=sd)

    def _evict_if_needed(self) -> None:
        while len(self._pool) >= self._max_size:
            oldest_pid = next(iter(self._pool), None)
            if oldest_pid is None:
                break
            self._close_entry(oldest_pid)

    def _close_entry(self, project_id: str) -> None:
        entry = self._pool.pop(project_id, None)
        if entry is not None:
            try:
                entry.db.close()
                logger.debug("Pool: closed entry for project %s", project_id)
            except Exception:
                logger.exception("Pool: error closing db for project %s", project_id)


# Module-level singleton
project_pool = ProjectDBPool()
