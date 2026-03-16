"""Session report jobs store — queued report generation tasks."""

from __future__ import annotations

import uuid
from typing import Any

from pixl.storage.db.base import BaseStore


class SessionReportDB(BaseStore):
    """CRUD for the session_report_jobs table."""

    def _row_to_dict(self, row) -> dict[str, Any]:
        return dict(row) if row else {}

    def enqueue_session_report_job(
        self,
        session_id: str,
        trigger: str = "manual_draft",
        terminal_status: str | None = None,
        requested_by: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        with self._db.write() as conn:
            conn.execute(
                """INSERT INTO session_report_jobs
                   (id, session_id, trigger, terminal_status, requested_by, idempotency_key)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, session_id, trigger, terminal_status, requested_by, idempotency_key),
            )
        return {"id": job_id, "session_id": session_id, "trigger": trigger, "status": "queued"}

    def enqueue_or_get_inflight_session_report_job(
        self,
        session_id: str,
        trigger: str = "manual_draft",
        terminal_status: str | None = None,
        requested_by: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_inflight_session_report_job(session_id=session_id, trigger=trigger)
        if existing:
            return existing
        return self.enqueue_session_report_job(
            session_id=session_id,
            trigger=trigger,
            terminal_status=terminal_status,
            requested_by=requested_by,
        )

    def claim_next_session_report_job(self) -> dict[str, Any] | None:
        with self._db.write() as conn:
            row = conn.execute(
                """SELECT * FROM session_report_jobs
                   WHERE status = 'queued'
                   ORDER BY created_at ASC LIMIT 1"""
            ).fetchone()
            if not row:
                return None
            job = self._row_to_dict(row)
            conn.execute(
                """UPDATE session_report_jobs
                   SET status = 'running', started_at = datetime('now'), updated_at = datetime('now')
                   WHERE id = ?""",
                (job["id"],),
            )
            job["status"] = "running"
            return job

    def get_session_report_job(self, job_id: str, **kwargs) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM session_report_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_session_report_jobs(
        self,
        session_id: str | None = None,
        status: str | None = None,
        trigger: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._build_where(
            {"session_id": session_id, "status": status, "trigger": trigger}
        )
        query = f"SELECT * FROM session_report_jobs {where} ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params = list(params) + [limit]
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_inflight_session_report_job(
        self,
        session_id: str | None = None,
        trigger: str | None = None,
    ) -> dict[str, Any] | None:
        conditions = ["status IN ('queued', 'running')"]
        params: list[Any] = []
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if trigger:
            conditions.append("trigger = ?")
            params.append(trigger)
        row = self._conn.execute(
            f"SELECT * FROM session_report_jobs WHERE {' AND '.join(conditions)} ORDER BY created_at DESC LIMIT 1",
            params,
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def complete_session_report_job(self, job_id: str, artifact_id: str) -> bool:
        with self._db.write() as conn:
            cursor = conn.execute(
                """UPDATE session_report_jobs
                   SET status = 'completed', artifact_id = ?, completed_at = datetime('now'), updated_at = datetime('now')
                   WHERE id = ? AND status = 'running'""",
                (artifact_id, job_id),
            )
            return cursor.rowcount > 0

    def fail_session_report_job(self, job_id: str, error_message: str) -> bool:
        with self._db.write() as conn:
            cursor = conn.execute(
                """UPDATE session_report_jobs
                   SET status = 'failed', error_message = ?, completed_at = datetime('now'), updated_at = datetime('now')
                   WHERE id = ? AND status = 'running'""",
                (error_message, job_id),
            )
            return cursor.rowcount > 0

    def requeue_session_report_job(self, job_id: str) -> bool:
        with self._db.write() as conn:
            cursor = conn.execute(
                """UPDATE session_report_jobs
                   SET status = 'queued', started_at = NULL, retry_count = retry_count + 1, updated_at = datetime('now')
                   WHERE id = ?""",
                (job_id,),
            )
            return cursor.rowcount > 0

    def requeue_stale_session_report_jobs(self, max_running_seconds: int = 900) -> int:
        with self._db.write() as conn:
            cursor = conn.execute(
                """UPDATE session_report_jobs
                   SET status = 'queued', started_at = NULL, retry_count = retry_count + 1, updated_at = datetime('now')
                   WHERE status = 'running'
                     AND started_at IS NOT NULL
                     AND (julianday('now') - julianday(started_at)) * 86400 > ?""",
                (max_running_seconds,),
            )
            return cursor.rowcount
