"""Wakeup queue store — serialized session triggers with coalescing.

Write serialization is handled by PixlDB.write() which holds a threading
lock. Per-session coalescing merges redundant pending wakeups.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from pixl.storage.db.base import BaseStore


class WakeupQueueDB(BaseStore):
    """Wakeup request queue backed by SQLite."""

    def enqueue(
        self,
        session_id: str,
        reason: str,
        payload: dict | None = None,
    ) -> int:
        """Add a wakeup request. Returns the request ID."""
        payload_json = json.dumps(payload) if payload else None
        with self._db.write() as conn:
            cursor = conn.execute(
                """INSERT INTO wakeup_requests (session_id, reason, payload_json)
                   VALUES (?, ?, ?)""",
                (session_id, reason, payload_json),
            )
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    def dequeue_next(self) -> dict[str, Any] | None:
        """Atomically claim the oldest pending request.

        Write lock is held by the write() context manager, preventing
        concurrent dequeue races.
        """
        with self._db.write() as conn:
            row = conn.execute(
                """SELECT * FROM wakeup_requests
                   WHERE status = 'pending'
                   ORDER BY created_at ASC
                   LIMIT 1"""
            ).fetchone()

            if not row:
                return None

            request = dict(row)
            conn.execute(
                """UPDATE wakeup_requests
                   SET status = 'processing', processed_at = ?
                   WHERE id = ?""",
                (datetime.now().isoformat(), request["id"]),
            )
            conn.commit()
            return request

    def coalesce_pending(self, session_id: str) -> int:
        """Coalesce redundant pending requests for a session.

        Keeps the oldest pending request and marks others as coalesced.
        Returns the number of coalesced requests.
        """
        with self._db.write() as conn:
            rows = conn.execute(
                """SELECT id FROM wakeup_requests
                   WHERE session_id = ? AND status = 'pending'
                   ORDER BY created_at ASC""",
                (session_id,),
            ).fetchall()

            if len(rows) <= 1:
                return 0

            # Keep first, coalesce rest
            keep_id = rows[0]["id"]
            coalesce_ids = [r["id"] for r in rows[1:]]
            count = len(coalesce_ids)

            placeholders = ",".join("?" * count)
            conn.execute(
                f"""UPDATE wakeup_requests
                    SET status = 'coalesced'
                    WHERE id IN ({placeholders})""",
                coalesce_ids,
            )
            conn.execute(
                "UPDATE wakeup_requests SET coalesced_count = ? WHERE id = ?",
                (count, keep_id),
            )
            conn.commit()
            return count

    def complete(self, request_id: int) -> None:
        """Mark a request as completed."""
        with self._db.write() as conn:
            conn.execute(
                "UPDATE wakeup_requests SET status = 'completed' WHERE id = ?",
                (request_id,),
            )
            conn.commit()

    def fail(self, request_id: int, error: str | None = None) -> None:
        """Mark a request as failed."""
        with self._db.write() as conn:
            conn.execute(
                "UPDATE wakeup_requests SET status = 'failed' WHERE id = ?",
                (request_id,),
            )
            conn.commit()

    def pending_count(self, session_id: str | None = None) -> int:
        """Count pending requests, optionally filtered by session."""
        if session_id:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM wakeup_requests WHERE status = 'pending' AND session_id = ?",
                (session_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM wakeup_requests WHERE status = 'pending'"
            ).fetchone()
        return row["cnt"] if row else 0

    def has_active_processing(self, session_id: str, exclude_id: int | None = None) -> bool:
        """Check if a session already has a request being processed."""
        if exclude_id is not None:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM wakeup_requests WHERE status = 'processing' AND session_id = ? AND id != ?",
                (session_id, exclude_id),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM wakeup_requests WHERE status = 'processing' AND session_id = ?",
                (session_id,),
            ).fetchone()
        return (row["cnt"] if row else 0) > 0

    def defer(self, request_id: int) -> None:
        """Mark a request as deferred (resource locked, promote later)."""
        with self._db.write() as conn:
            conn.execute(
                "UPDATE wakeup_requests SET status = 'deferred' WHERE id = ?",
                (request_id,),
            )
            conn.commit()

    def promote_orphaned_deferred(self) -> int:
        """Promote deferred requests that have no active processing request.

        Recovers from situations where all requests for a session are
        deferred but nothing is processing — a deadlock state.
        """
        with self._db.write() as conn:
            cursor = conn.execute(
                """UPDATE wakeup_requests
                   SET status = 'pending'
                   WHERE status = 'deferred'
                     AND session_id NOT IN (
                         SELECT DISTINCT session_id FROM wakeup_requests
                         WHERE status = 'processing'
                     )"""
            )
            conn.commit()
            return cursor.rowcount

    def promote_deferred(self, session_id: str) -> int:
        """Promote deferred requests back to pending for a session.

        Called when a lock releases (gate approved, node finished, budget reset).
        Returns the number of promoted requests.
        """
        with self._db.write() as conn:
            cursor = conn.execute(
                """UPDATE wakeup_requests
                   SET status = 'pending'
                   WHERE session_id = ? AND status = 'deferred'""",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount
