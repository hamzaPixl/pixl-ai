"""Workflow session store in SQLite.

Replaces the file-based session storage (session.json per session directory)
with proper relational tables. Node instances and loop states are stored
in their own tables rather than as nested JSON, enabling queries like
"find all sessions with failed nodes" or "show all running tasks".

The snapshot is still stored as JSON blob since its internal structure
isn't queried directly — it's loaded whole for graph execution.

THREAD SAFETY: Receives PixlDB and gets thread-local connections
for each operation, making it safe for concurrent use.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from pixl.models.session import STALENESS_THRESHOLD_SECONDS
from pixl.storage.db.base import BaseStore


class SessionDB(BaseStore):
    """Workflow session store backed by SQLite.

    Replaces:
    - storage/workflow_session_store.py (file-based)
    - storage/session_store.py (SDK sessions)
    - storage/snapshot_store.py (snapshot storage)

    Receives a PixlDB instance and obtains thread-local connections
    for each operation, making it safe for multi-threaded use.
    """

    # Workflow sessions

    def create_session(
        self,
        feature_id: str,
        snapshot_hash: str,
        baseline_commit: str | None = None,
        workspace_root: str | None = None,
        workflow_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new workflow session.

        `workflow_id` and `metadata` are accepted for backward compatibility
        with older call sites and test fixtures. They are currently not
        persisted in `workflow_sessions` schema.

        Returns the created session dict.
        """
        _ = workflow_id
        _ = metadata
        session_id = f"sess-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO workflow_sessions
               (id, feature_id, snapshot_hash, created_at, last_updated_at,
                baseline_commit, workspace_root)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, feature_id, snapshot_hash, now, now, baseline_commit, workspace_root),
        )
        self._conn.commit()
        return self.get_session(session_id)  # type: ignore

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a workflow session with all its state."""
        row = self._conn.execute(
            "SELECT * FROM workflow_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None

        session = dict(row)

        if session.get("frozen_artifacts"):
            try:
                session["frozen_artifacts"] = json.loads(session["frozen_artifacts"])
            except (json.JSONDecodeError, TypeError):
                session["frozen_artifacts"] = {}

        # Batch-deserialize all JSON-suffixed fields
        self._deserialize_json(
            session,
            {
                "cursor_json": "cursor",
                "structured_outputs_json": "structured_outputs",
                "session_state_json": "session_state",
                "baton_json": "baton",
                "baton_history_json": "baton_history",
                "context_audit_json": "context_audit",
            },
            defaults={
                "structured_outputs": {},
                "session_state": {},
                "baton_history": [],
                "context_audit": [],
            },
        )

        node_rows = self._conn.execute(
            "SELECT * FROM node_instances WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        session["node_instances"] = {r["node_id"]: self._node_to_dict(r) for r in node_rows}

        loop_rows = self._conn.execute(
            "SELECT * FROM loop_states WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        session["loop_state"] = {r["loop_id"]: self._loop_to_dict(r) for r in loop_rows}

        # Prefer stored status (set on transitions), fall back to computed
        stored = session.get("status")
        if stored and stored not in ("created", None):
            session["status"] = stored
        else:
            session["status"] = self._compute_status(
                session["node_instances"],
                session.get("paused_at"),
                session.get("ended_at"),
                session.get("last_updated_at"),
            )

        # Detect orphaned running sessions via staleness
        session["is_orphaned"] = False
        if session["status"] == "running":
            age = self._session_age_seconds(session.get("last_updated_at"))
            session["is_orphaned"] = age is not None and age > STALENESS_THRESHOLD_SECONDS

        if session["is_orphaned"] and session["status"] == "running":
            session["status"] = "stalled"

        # Self-heal zombie sessions: all nodes terminal but ended_at missing.
        if session["status"] == "running" and not session.get("ended_at"):
            if self._all_nodes_terminal(session["node_instances"]):
                import logging as _logging

                now = datetime.now().isoformat()
                self.update_session(session_id, ended_at=now)
                session["ended_at"] = now
                session["status"] = self._compute_status(
                    session["node_instances"],
                    session.get("paused_at"),
                    session["ended_at"],
                    session.get("last_updated_at"),
                )
                _logging.getLogger(__name__).warning("Self-healed zombie session %s", session_id)

        session["execution_seconds"] = self._sum_node_durations(session["node_instances"])

        return session

    def update_session(self, session_id: str, **fields) -> bool:
        """Update session-level fields."""
        if "cursor" in fields:
            fields["cursor_json"] = json.dumps(fields.pop("cursor"))
        if "frozen_artifacts" in fields:
            fields["frozen_artifacts"] = json.dumps(fields["frozen_artifacts"])
        if "structured_outputs" in fields:
            fields["structured_outputs_json"] = json.dumps(fields.pop("structured_outputs"))
        if "session_state" in fields:
            fields["session_state_json"] = json.dumps(fields.pop("session_state"))

        fields["last_updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [session_id]
        cursor = self._conn.execute(
            f"UPDATE workflow_sessions SET {set_clause} WHERE id = ?", values
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all associated data (cascading)."""
        cursor = self._conn.execute("DELETE FROM workflow_sessions WHERE id = ?", (session_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def list_sessions(
        self,
        feature_id: str | None = None,
        limit: int | None = None,
        status: str | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """List sessions, optionally filtered by feature and status.

        Args:
            feature_id: Filter by feature ID
            limit: Maximum number of sessions to return
            status: Filter by session status (running, completed, failed, paused)
            offset: Number of sessions to skip

        Returns:
            List of session dictionaries with lightweight data
        """
        conditions = []
        params: list[Any] = []

        if feature_id:
            conditions.append("ws.feature_id = ?")
            params.append(feature_id)

        if status:
            if status == "running":
                # Only truly running: not ended, not paused, has an active task,
                # and no gates waiting
                conditions.append("""ws.ended_at IS NULL AND ws.paused_at IS NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM node_instances ni
                        WHERE ni.session_id = ws.id
                        AND ni.state IN ('gate_waiting', 'task_blocked')
                    )
                    AND EXISTS (
                        SELECT 1 FROM node_instances ni
                        WHERE ni.session_id = ws.id AND ni.state = 'task_running'
                    )""")
            elif status == "paused":
                # Explicitly paused OR gate-paused
                conditions.append("""(ws.paused_at IS NOT NULL OR EXISTS (
                    SELECT 1 FROM node_instances ni
                    WHERE ni.session_id = ws.id
                    AND ni.state IN ('gate_waiting', 'task_blocked')
                ))""")
            elif status == "completed":
                conditions.append("ws.ended_at IS NOT NULL")
            elif status == "failed":
                conditions.append("""EXISTS (
                    SELECT 1 FROM node_instances ni
                    WHERE ni.session_id = ws.id
                    AND ni.state IN ('task_failed', 'gate_rejected')
                )
                    AND ws.paused_at IS NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM node_instances ni
                        WHERE ni.session_id = ws.id
                        AND ni.state IN ('task_running', 'gate_waiting', 'task_blocked')
                )""")
            elif status == "stalled":
                # Zombie sessions: not ended, no active nodes, last_updated_at stale
                conditions.append("""ws.ended_at IS NULL
                    AND ws.paused_at IS NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM node_instances ni
                        WHERE ni.session_id = ws.id AND ni.state IN ('task_running', 'gate_waiting')
                    )
                    AND ws.last_updated_at < datetime('now', ?)""")
                params.append(f"-{STALENESS_THRESHOLD_SECONDS} seconds")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT ws.id, ws.feature_id, ws.created_at, ws.last_updated_at,
                   ws.ended_at, ws.paused_at, ws.baseline_commit, ws.status
            FROM workflow_sessions ws
            {where}
            ORDER BY ws.created_at DESC
        """

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        if offset:
            query += " OFFSET ?"
            params.append(offset)

        rows = self._conn.execute(query, params).fetchall()

        sessions = []
        for row in rows:
            session = dict(row)
            node_rows = self._conn.execute(
                "SELECT * FROM node_instances WHERE session_id = ?",
                (session["id"],),
            ).fetchall()
            session["node_instances"] = {r["node_id"]: self._node_to_dict(r) for r in node_rows}
            stored = session.get("status")
            if stored and stored not in ("created", None):
                session["status"] = stored
            else:
                session["status"] = self._compute_status(
                    session["node_instances"],
                    session.get("paused_at"),
                    session.get("ended_at"),
                    session.get("last_updated_at"),
                )
            session["execution_seconds"] = self._sum_node_durations(session["node_instances"])
            sessions.append(session)

        return sessions

    def get_latest_session(self, feature_id: str | None = None) -> dict[str, Any] | None:
        """Get the most recent session."""
        sessions = self.list_sessions(feature_id=feature_id, limit=1)
        return sessions[0] if sessions else None

    def touch_session(self, session_id: str) -> bool:
        """Lightweight heartbeat — only updates last_updated_at."""
        now = datetime.now().isoformat()
        cursor = self._conn.execute(
            "UPDATE workflow_sessions SET last_updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_active_sessions(self) -> list[dict[str, Any]]:
        """Get sessions that haven't ended yet."""
        rows = self._conn.execute(
            "SELECT id FROM workflow_sessions WHERE ended_at IS NULL ORDER BY created_at DESC"
        ).fetchall()
        return [self.get_session(r["id"]) for r in rows]  # type: ignore

    def get_recent_sessions(self, limit: int = 15) -> list[dict[str, Any]]:
        """Get most recent sessions regardless of status, ordered by created_at desc."""
        rows = self._conn.execute(
            "SELECT id FROM workflow_sessions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        results = []
        for r in rows:
            s = self.get_session(r["id"])
            if s:
                results.append(s)
        return results

    # Session report jobs (delegated to SessionReportDB)

    def _report_db(self):
        """Lazy access to the session report store."""
        return self._db.session_reports

    def enqueue_session_report_job(self, **kwargs) -> dict[str, Any]:
        return self._report_db().enqueue_session_report_job(**kwargs)

    def enqueue_or_get_inflight_session_report_job(self, **kwargs) -> dict[str, Any]:
        return self._report_db().enqueue_or_get_inflight_session_report_job(**kwargs)

    def claim_next_session_report_job(self) -> dict[str, Any] | None:
        return self._report_db().claim_next_session_report_job()

    def get_session_report_job(self, job_id: str, **kwargs) -> dict[str, Any] | None:
        return self._report_db().get_session_report_job(job_id, **kwargs)

    def list_session_report_jobs(self, **kwargs) -> list[dict[str, Any]]:
        return self._report_db().list_session_report_jobs(**kwargs)

    def get_inflight_session_report_job(self, **kwargs) -> dict[str, Any] | None:
        return self._report_db().get_inflight_session_report_job(**kwargs)

    def complete_session_report_job(self, job_id: str, artifact_id: str) -> bool:
        return self._report_db().complete_session_report_job(job_id, artifact_id)

    def fail_session_report_job(self, job_id: str, error_message: str) -> bool:
        return self._report_db().fail_session_report_job(job_id, error_message)

    def requeue_session_report_job(self, job_id: str) -> bool:
        return self._report_db().requeue_session_report_job(job_id)

    def requeue_stale_session_report_jobs(self, max_running_seconds: int = 900) -> int:
        return self._report_db().requeue_stale_session_report_jobs(max_running_seconds)

    # Staleness detection (replaces lease-based orphan detection)

    def list_stalled_running_sessions(self, stale_after_seconds: int | None = None) -> list[str]:
        """List running sessions whose last_updated_at exceeds the staleness threshold."""
        threshold = (
            stale_after_seconds if stale_after_seconds is not None else STALENESS_THRESHOLD_SECONDS
        )
        rows = self._conn.execute(
            """SELECT id, paused_at, ended_at, last_updated_at
               FROM workflow_sessions
               WHERE ended_at IS NULL
               ORDER BY created_at DESC"""
        ).fetchall()

        stalled: list[str] = []
        for row in rows:
            session_id = str(row["id"])
            node_rows = self._conn.execute(
                "SELECT * FROM node_instances WHERE session_id = ?",
                (session_id,),
            ).fetchall()
            node_instances = {r["node_id"]: self._node_to_dict(r) for r in node_rows}
            status = self._compute_status(
                node_instances,
                row["paused_at"],
                row["ended_at"],
                row["last_updated_at"],
            )
            if status != "running":
                continue

            age = self._session_age_seconds(row["last_updated_at"])
            if age is not None and age > threshold:
                stalled.append(session_id)

        return stalled

    # Node instances

    def upsert_node_instance(
        self,
        session_id: str,
        node_id: str,
        state: str,
        attempt: int = 0,
        blocked_reason: str | None = None,
        output: dict[str, Any] | None = None,
        failure_kind: str | None = None,
        error_message: str | None = None,
        model_name: str | None = None,
        agent_name: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Create or update a node instance."""
        now = datetime.now().isoformat()
        output_json = json.dumps(output) if output else None

        # Determine timestamps based on state
        started_at = now if state.endswith("_running") else None
        ended_at = (
            now
            if state.endswith(
                ("_completed", "_failed", "_rejected", "_timeout", "_approved", "_skipped")
            )
            else None
        )

        self._conn.execute(
            """INSERT INTO node_instances
               (session_id, node_id, state, attempt, ready_at, started_at, ended_at,
                blocked_reason, output_json, failure_kind, error_message,
                model_name, agent_name, input_tokens, output_tokens, total_tokens, cost_usd)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id, node_id) DO UPDATE SET
                 state = excluded.state,
                 attempt = excluded.attempt,
                 started_at = COALESCE(excluded.started_at, node_instances.started_at),
                 ended_at = excluded.ended_at,
                 blocked_reason = excluded.blocked_reason,
                 output_json = COALESCE(excluded.output_json, node_instances.output_json),
                 failure_kind = excluded.failure_kind,
                 error_message = excluded.error_message,
                 model_name = COALESCE(excluded.model_name, node_instances.model_name),
                 agent_name = COALESCE(excluded.agent_name, node_instances.agent_name),
                 input_tokens = node_instances.input_tokens + excluded.input_tokens,
                 output_tokens = node_instances.output_tokens + excluded.output_tokens,
                 total_tokens = node_instances.total_tokens + excluded.total_tokens,
                 cost_usd = node_instances.cost_usd + excluded.cost_usd""",
            (
                session_id,
                node_id,
                state,
                attempt,
                now,
                started_at,
                ended_at,
                blocked_reason,
                output_json,
                failure_kind,
                error_message,
                model_name,
                agent_name,
                input_tokens,
                output_tokens,
                total_tokens,
                cost_usd,
            ),
        )

        self._conn.execute(
            "UPDATE workflow_sessions SET last_updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self._conn.commit()

    def get_node_instance(self, session_id: str, node_id: str) -> dict[str, Any] | None:
        """Get a specific node instance."""
        row = self._conn.execute(
            "SELECT * FROM node_instances WHERE session_id = ? AND node_id = ?",
            (session_id, node_id),
        ).fetchone()
        return self._node_to_dict(row) if row else None

    def get_nodes_by_state(self, session_id: str, state: str) -> list[dict[str, Any]]:
        """Get all nodes in a specific state within a session."""
        rows = self._conn.execute(
            "SELECT * FROM node_instances WHERE session_id = ? AND state = ?",
            (session_id, state),
        ).fetchall()
        return [self._node_to_dict(r) for r in rows]

    def unblock_tasks_for_resume(self, session_id: str) -> list[str]:
        """Move blocked, orphaned running, and failed nodes back to pending for resume.

        Handles three cases:
        1. task_blocked nodes — explicitly blocked, reset to pending.
        2. task_running nodes — orphaned by crash/restart mid-execution,
           reset to pending so they get re-enqueued. The metadata_json
           (containing llm_session_id) is preserved so the LLM conversation
           can be resumed.
        3. task_failed nodes — exhausted retries or crashed, reset to pending
           so the executor picks them up again on resume.

        The executor cursor is NOT cleared — _compute_ready_queue will
        naturally recompute the ready set from persisted node states.
        """
        blocked_rows = self._conn.execute(
            """SELECT node_id FROM node_instances
               WHERE session_id = ? AND state = ?""",
            (session_id, "task_blocked"),
        ).fetchall()
        blocked_nodes = [row["node_id"] for row in blocked_rows]

        # Also recover nodes stuck in task_running (orphaned by crash/restart)
        running_rows = self._conn.execute(
            """SELECT node_id FROM node_instances
               WHERE session_id = ? AND state = ?""",
            (session_id, "task_running"),
        ).fetchall()
        running_nodes = [row["node_id"] for row in running_rows]

        # Also recover failed nodes so the executor can retry them
        failed_rows = self._conn.execute(
            """SELECT node_id FROM node_instances
               WHERE session_id = ? AND state = ?""",
            (session_id, "task_failed"),
        ).fetchall()
        failed_nodes = [row["node_id"] for row in failed_rows]

        now = datetime.now().isoformat()
        if blocked_nodes:
            self._conn.execute(
                """UPDATE node_instances
                   SET state = ?,
                       blocked_reason = NULL,
                       started_at = NULL,
                       ended_at = NULL,
                       failure_kind = NULL,
                       error_message = NULL
                   WHERE session_id = ? AND state = ?""",
                ("task_pending", session_id, "task_blocked"),
            )
        if running_nodes:
            # execute_with_orchestrator knows this is a resumed execution
            # and will use the preserved llm_session_id.
            self._conn.execute(
                """UPDATE node_instances
                   SET state = ?,
                       started_at = NULL,
                       ended_at = NULL,
                       attempt = attempt + 1
                   WHERE session_id = ? AND state = ?""",
                ("task_pending", session_id, "task_running"),
            )
        if failed_nodes:
            self._conn.execute(
                """UPDATE node_instances
                   SET state = ?,
                       started_at = NULL,
                       ended_at = NULL,
                       failure_kind = NULL,
                       error_message = NULL,
                       attempt = attempt + 1
                   WHERE session_id = ? AND state = ?""",
                ("task_pending", session_id, "task_failed"),
            )
        self.reset_loop_states(session_id)

        self._conn.execute(
            """UPDATE workflow_sessions
               SET last_updated_at = ?
               WHERE id = ?""",
            (now, session_id),
        )
        self._conn.commit()
        return blocked_nodes + running_nodes + failed_nodes

    def force_unblock_for_resume(self, session_id: str) -> list[str]:
        """Like unblock_tasks_for_resume but also resets gate_waiting nodes.

        Used by force-resume when gates are stuck after an executor crash.
        Returns all node IDs that were reset.
        """
        unblocked = self.unblock_tasks_for_resume(session_id)

        gate_rows = self._conn.execute(
            """SELECT node_id FROM node_instances
               WHERE session_id = ? AND state = ?""",
            (session_id, "gate_waiting"),
        ).fetchall()
        gate_nodes = [row["node_id"] for row in gate_rows]

        if gate_nodes:
            self._conn.execute(
                """UPDATE node_instances
                   SET state = ?,
                       started_at = NULL,
                       ended_at = NULL
                   WHERE session_id = ? AND state = ?""",
                ("task_pending", session_id, "gate_waiting"),
            )
            self._conn.commit()

        return unblocked + gate_nodes

    def find_sessions_with_failed_nodes(self) -> list[str]:
        """Find session IDs that have failed nodes."""
        rows = self._conn.execute(
            """SELECT DISTINCT session_id FROM node_instances
               WHERE state = 'task_failed'"""
        ).fetchall()
        return [r["session_id"] for r in rows]

    def upsert_loop_state(
        self,
        session_id: str,
        loop_id: str,
        current_iteration: int,
        max_iterations: int,
        history: list[dict] | None = None,
    ) -> None:
        """Create or update a loop state."""
        history_json = json.dumps(history or [])

        self._conn.execute(
            """INSERT INTO loop_states
               (session_id, loop_id, current_iteration, max_iterations, history_json)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(session_id, loop_id) DO UPDATE SET
                 current_iteration = excluded.current_iteration,
                 history_json = excluded.history_json""",
            (session_id, loop_id, current_iteration, max_iterations, history_json),
        )
        self._conn.commit()

    def reset_loop_states(self, session_id: str) -> int:
        """Reset all loop states to iteration 0 for a session. Returns count reset."""
        cursor = self._conn.execute(
            "UPDATE loop_states SET current_iteration = 0 WHERE session_id = ?",
            (session_id,),
        )
        self._conn.commit()
        return cursor.rowcount

    def get_loop_state(self, session_id: str, loop_id: str) -> dict[str, Any] | None:
        """Get loop state."""
        row = self._conn.execute(
            "SELECT * FROM loop_states WHERE session_id = ? AND loop_id = ?",
            (session_id, loop_id),
        ).fetchone()
        return self._loop_to_dict(row) if row else None

    # Snapshots

    def save_snapshot(self, snapshot_hash: str, snapshot_json: str) -> None:
        """Save a workflow snapshot (idempotent)."""
        self._conn.execute(
            """INSERT OR IGNORE INTO workflow_snapshots (snapshot_hash, snapshot_json)
               VALUES (?, ?)""",
            (snapshot_hash, snapshot_json),
        )
        self._conn.commit()

    def get_snapshot(self, snapshot_hash: str) -> str | None:
        """Get snapshot JSON by hash."""
        row = self._conn.execute(
            "SELECT snapshot_json FROM workflow_snapshots WHERE snapshot_hash = ?",
            (snapshot_hash,),
        ).fetchone()
        return row["snapshot_json"] if row else None

    def snapshot_exists(self, snapshot_hash: str) -> bool:
        """Check if a snapshot exists."""
        row = self._conn.execute(
            "SELECT 1 FROM workflow_snapshots WHERE snapshot_hash = ?",
            (snapshot_hash,),
        ).fetchone()
        return row is not None

    def cleanup_orphaned_snapshots(self, active_hashes: set[str]) -> int:
        """Remove snapshots not referenced by any session."""
        all_hashes = self._conn.execute("SELECT snapshot_hash FROM workflow_snapshots").fetchall()

        removed = 0
        for row in all_hashes:
            if row["snapshot_hash"] not in active_hashes:
                self._conn.execute(
                    "DELETE FROM workflow_snapshots WHERE snapshot_hash = ?",
                    (row["snapshot_hash"],),
                )
                removed += 1

        if removed:
            self._conn.commit()
        return removed

    # Internal helpers

    def _node_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert node instance row to dict."""
        d = dict(row)
        self._deserialize_json(d, {"output_json": "output"})

        # metadata_json is special: its keys are merged into the top-level dict
        raw_meta = d.pop("metadata_json", None)
        metadata: dict[str, Any] = {}
        if raw_meta:
            try:
                metadata = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                d.setdefault(key, value)
        return d

    def _loop_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert loop state row to dict."""
        d = dict(row)
        self._deserialize_json(d, {"history_json": "history"}, defaults={"history": []})
        return d

    @staticmethod
    def _sum_node_durations(node_instances: dict[str, dict]) -> float:
        """Sum execution time of all node instances that have both started_at and ended_at."""
        total = 0.0
        for node in node_instances.values():
            started = node.get("started_at")
            ended = node.get("ended_at")
            if started and ended:
                try:
                    s = datetime.fromisoformat(started)
                    e = datetime.fromisoformat(ended)
                    total += max((e - s).total_seconds(), 0.0)
                except (ValueError, TypeError):
                    pass
        return round(total, 1)

    def _compute_status(
        self,
        node_instances: dict[str, dict],
        paused_at: str | None = None,
        ended_at: str | None = None,
        last_updated_at: str | None = None,
    ) -> str:
        """Compute session status from node states.

        Delegates to WorkflowSession.status to keep a single source of truth.
        """
        from pixl.models.session import WorkflowSession

        temp = WorkflowSession(
            id="tmp",
            feature_id="tmp",
            snapshot_hash="tmp",
            node_instances=node_instances,
            paused_at=datetime.fromisoformat(paused_at)
            if isinstance(paused_at, str)
            else paused_at,
            ended_at=datetime.fromisoformat(ended_at) if isinstance(ended_at, str) else ended_at,
            last_updated_at=datetime.fromisoformat(last_updated_at)
            if isinstance(last_updated_at, str)
            else last_updated_at,
        )
        return temp.status.value

    @staticmethod
    def _session_age_seconds(last_updated_at: Any) -> float | None:
        """Seconds since last_updated_at, or None if unparseable."""
        if not last_updated_at:
            return None
        try:
            if isinstance(last_updated_at, str):
                parsed = datetime.fromisoformat(last_updated_at)
            elif isinstance(last_updated_at, datetime):
                parsed = last_updated_at
            else:
                return None
            now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
            return max((now - parsed).total_seconds(), 0.0)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _all_nodes_terminal(node_instances: dict[str, dict]) -> bool:
        """Return True when every node instance is in a terminal state."""
        if not node_instances:
            return False
        terminal = {
            "task_completed",
            "gate_approved",
            "task_skipped",
            "task_failed",
            "gate_rejected",
        }
        return all(n.get("state") in terminal for n in node_instances.values())

    # Node execution locks (Phase 5)

    def lock_node(self, session_id: str, node_id: str, run_id: str) -> bool:
        """Acquire an execution lock on a node.

        Uses BEGIN IMMEDIATE for SQLite-level write locking to prevent
        concurrent execution of the same node.

        Returns True if lock acquired, False if already locked.
        """
        now = datetime.now().isoformat()
        with self._db.write() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT execution_run_id, execution_locked_at
                   FROM node_instances
                   WHERE session_id = ? AND node_id = ?""",
                (session_id, node_id),
            ).fetchone()

            if row and row["execution_run_id"]:
                # Already locked — check if stale (> 120s)
                locked_at = row["execution_locked_at"]
                if locked_at:
                    try:
                        age = (datetime.now() - datetime.fromisoformat(locked_at)).total_seconds()
                        if age < 120:
                            conn.execute("COMMIT")
                            return False
                    except (ValueError, TypeError):
                        pass

            conn.execute(
                """UPDATE node_instances
                   SET execution_run_id = ?, execution_locked_at = ?
                   WHERE session_id = ? AND node_id = ?""",
                (run_id, now, session_id, node_id),
            )
            conn.execute("COMMIT")
            return True

    def release_node(self, session_id: str, node_id: str, run_id: str) -> None:
        """Release an execution lock on a node.

        Only releases if the lock is held by the given run_id.
        """
        with self._db.write() as conn:
            conn.execute(
                """UPDATE node_instances
                   SET execution_run_id = NULL, execution_locked_at = NULL
                   WHERE session_id = ? AND node_id = ? AND execution_run_id = ?""",
                (session_id, node_id, run_id),
            )
            conn.commit()
