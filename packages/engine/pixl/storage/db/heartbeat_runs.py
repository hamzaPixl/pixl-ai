"""Heartbeat run store — CRUD for execution windows.

Each heartbeat run tracks a bounded execution period within a session.
The heartbeat_at column is updated every 30s by the runner, providing
authoritative liveness detection (stalled = no heartbeat in 60s).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pixl.storage.db.base import BaseStore


class HeartbeatRunDB(BaseStore):
    """Heartbeat run store backed by SQLite."""

    def create_run(
        self,
        run_id: str,
        session_id: str,
        invocation: str = "start",
        context_snapshot: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new queued heartbeat run."""
        now = datetime.now().isoformat()
        snapshot_json = json.dumps(context_snapshot) if context_snapshot else None

        with self._db.write() as conn:
            conn.execute(
                """INSERT INTO heartbeat_runs
                   (id, session_id, status, invocation, context_snapshot, created_at)
                   VALUES (?, ?, 'queued', ?, ?, ?)""",
                (run_id, session_id, invocation, snapshot_json, now),
            )
            # Set as current run on session
            conn.execute(
                "UPDATE workflow_sessions SET current_run_id = ? WHERE id = ?",
                (run_id, session_id),
            )
            conn.commit()

        return self.get_run(run_id)  # type: ignore[return-value]

    def start_run(self, run_id: str) -> None:
        """Transition run from queued to running."""
        now = datetime.now().isoformat()
        with self._db.write() as conn:
            conn.execute(
                """UPDATE heartbeat_runs
                   SET status = 'running', started_at = ?, heartbeat_at = ?
                   WHERE id = ? AND status = 'queued'""",
                (now, now, run_id),
            )
            conn.commit()

    def heartbeat(self, run_id: str) -> None:
        """Update heartbeat timestamp for a running run."""
        now = datetime.now().isoformat()
        with self._db.write() as conn:
            conn.execute(
                "UPDATE heartbeat_runs SET heartbeat_at = ? WHERE id = ? AND status = 'running'",
                (now, run_id),
            )
            conn.commit()

    def complete_run(
        self,
        run_id: str,
        *,
        status: str = "succeeded",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        steps_executed: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Mark a run as terminal (succeeded, failed, cancelled, timed_out)."""
        now = datetime.now().isoformat()
        with self._db.write() as conn:
            conn.execute(
                """UPDATE heartbeat_runs
                   SET status = ?, ended_at = ?, heartbeat_at = ?,
                       input_tokens = ?, output_tokens = ?, cost_usd = ?,
                       steps_executed = ?, error_message = ?
                   WHERE id = ?""",
                (
                    status,
                    now,
                    now,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    steps_executed,
                    error_message,
                    run_id,
                ),
            )
            conn.commit()

    def fail_run(self, run_id: str, error_message: str) -> None:
        """Convenience: mark run as failed."""
        self.complete_run(run_id, status="failed", error_message=error_message)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a single run by ID."""
        row = self._conn.execute("SELECT * FROM heartbeat_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def list_for_session(self, session_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """List runs for a session, most recent first."""
        rows = self._conn.execute(
            "SELECT * FROM heartbeat_runs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_active_run(self, session_id: str) -> dict[str, Any] | None:
        """Get the currently running run for a session."""
        row = self._conn.execute(
            "SELECT * FROM heartbeat_runs WHERE session_id = ? AND status = 'running' LIMIT 1",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None

    def find_stalled_runs(self, threshold_seconds: int = 60) -> list[dict[str, Any]]:
        """Find running runs with stale heartbeats."""
        rows = self._conn.execute(
            """SELECT * FROM heartbeat_runs
               WHERE status = 'running'
               AND heartbeat_at IS NOT NULL
               AND (julianday('now') - julianday(heartbeat_at)) * 86400 > ?""",
            (threshold_seconds,),
        ).fetchall()
        return [dict(r) for r in rows]

    def increment_usage(
        self,
        run_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        steps: int = 0,
    ) -> None:
        """Atomically increment token/cost counters on a run."""
        with self._db.write() as conn:
            conn.execute(
                """UPDATE heartbeat_runs
                   SET input_tokens = input_tokens + ?,
                       output_tokens = output_tokens + ?,
                       cost_usd = cost_usd + ?,
                       steps_executed = steps_executed + ?
                   WHERE id = ?""",
                (input_tokens, output_tokens, cost_usd, steps, run_id),
            )
            conn.commit()
