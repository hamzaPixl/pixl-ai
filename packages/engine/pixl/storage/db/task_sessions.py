"""Task session store — adapter session persistence in SQLite."""

from __future__ import annotations

from pixl.storage.db.base import BaseStore


class TaskSessionDB(BaseStore):
    """Persists adapter session state for task resume across runs."""

    def get_task_session(self, session_id: str, task_key: str) -> dict | None:
        """Look up a task session by session_id and task_key."""
        row = self._conn.execute(
            "SELECT * FROM task_sessions WHERE session_id = ? AND task_key = ?",
            (session_id, task_key),
        ).fetchone()
        return dict(row) if row else None

    def upsert_task_session(
        self,
        session_id: str,
        node_id: str,
        task_key: str,
        adapter_name: str,
        adapter_session_id: str | None = None,
        last_run_id: str | None = None,
    ) -> None:
        """Insert or update a task session record."""
        with self._db.write() as conn:
            conn.execute(
                """INSERT INTO task_sessions
                   (session_id, node_id, task_key, adapter_name,
                    adapter_session_id, last_run_id, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(session_id, task_key) DO UPDATE SET
                       node_id = excluded.node_id,
                       adapter_name = excluded.adapter_name,
                       adapter_session_id = excluded.adapter_session_id,
                       last_run_id = excluded.last_run_id,
                       updated_at = datetime('now')""",
                (session_id, node_id, task_key, adapter_name, adapter_session_id, last_run_id),
            )
            conn.commit()
