"""Cost event store — per-execution cost tracking in SQLite."""

from __future__ import annotations

from datetime import datetime, timezone

from pixl.storage.db.base import BaseStore


class CostEventDB(BaseStore):
    """Persists cost events and provides budget aggregations."""

    def record(
        self,
        session_id: str,
        *,
        run_id: str | None = None,
        node_id: str | None = None,
        adapter_name: str | None = None,
        model_name: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Insert a cost event row."""
        with self._db.write() as conn:
            conn.execute(
                """INSERT INTO cost_events
                   (session_id, run_id, node_id, adapter_name, model_name,
                    input_tokens, output_tokens, cost_usd)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, run_id, node_id, adapter_name, model_name,
                 input_tokens, output_tokens, cost_usd),
            )
            conn.commit()

    def total_cost_for_month(self) -> float:
        """Sum cost_usd for the current calendar month."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        row = self._conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) AS total FROM cost_events WHERE created_at >= ?",
            (month_start.strftime("%Y-%m-%d %H:%M:%S"),),
        ).fetchone()
        return float(row["total"])

    def breakdown_by_adapter(self, session_id: str | None = None) -> list[dict]:
        """Group cost events by adapter_name, optionally filtered by session."""
        if session_id:
            rows = self._conn.execute(
                """SELECT adapter_name,
                          SUM(input_tokens) AS input_tokens,
                          SUM(output_tokens) AS output_tokens,
                          SUM(cost_usd) AS cost_usd,
                          COUNT(*) AS event_count
                   FROM cost_events
                   WHERE session_id = ?
                   GROUP BY adapter_name""",
                (session_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT adapter_name,
                          SUM(input_tokens) AS input_tokens,
                          SUM(output_tokens) AS output_tokens,
                          SUM(cost_usd) AS cost_usd,
                          COUNT(*) AS event_count
                   FROM cost_events
                   GROUP BY adapter_name""",
            ).fetchall()
        return [dict(r) for r in rows]
