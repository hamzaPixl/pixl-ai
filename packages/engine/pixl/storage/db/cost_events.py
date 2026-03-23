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

    def breakdown_by_model(self, session_id: str | None = None) -> list[dict]:
        """Cost breakdown grouped by model_name.

        Returns rows ordered by total cost descending, each containing:
        model_name, event_count, input_tokens, output_tokens, cost_usd.
        """
        if session_id:
            rows = self._conn.execute(
                """SELECT model_name,
                          COUNT(*) AS event_count,
                          SUM(input_tokens) AS input_tokens,
                          SUM(output_tokens) AS output_tokens,
                          SUM(cost_usd) AS cost_usd
                   FROM cost_events
                   WHERE session_id = ?
                   GROUP BY model_name
                   ORDER BY SUM(cost_usd) DESC""",
                (session_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT model_name,
                          COUNT(*) AS event_count,
                          SUM(input_tokens) AS input_tokens,
                          SUM(output_tokens) AS output_tokens,
                          SUM(cost_usd) AS cost_usd
                   FROM cost_events
                   GROUP BY model_name
                   ORDER BY SUM(cost_usd) DESC""",
            ).fetchall()
        return [dict(r) for r in rows]

    def total_by_session(self, limit: int = 20) -> list[dict]:
        """Total cost per session, ranked by cost descending.

        Returns rows containing: session_id, event_count,
        input_tokens, output_tokens, cost_usd.
        """
        rows = self._conn.execute(
            """SELECT session_id,
                      COUNT(*) AS event_count,
                      SUM(input_tokens) AS input_tokens,
                      SUM(output_tokens) AS output_tokens,
                      SUM(cost_usd) AS cost_usd
               FROM cost_events
               GROUP BY session_id
               ORDER BY SUM(cost_usd) DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> dict:
        """Overall cost summary.

        Returns a dict with: total_cost_usd, total_queries,
        total_input_tokens, total_output_tokens, top_model.
        """
        row = self._conn.execute(
            """SELECT COALESCE(SUM(cost_usd), 0.0) AS total_cost_usd,
                      COUNT(*) AS total_queries,
                      COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
                      COALESCE(SUM(output_tokens), 0) AS total_output_tokens
               FROM cost_events""",
        ).fetchone()

        result = dict(row)

        # Determine the model with the highest total cost
        top = self._conn.execute(
            """SELECT model_name
               FROM cost_events
               GROUP BY model_name
               ORDER BY SUM(cost_usd) DESC
               LIMIT 1""",
        ).fetchone()
        result["top_model"] = top["model_name"] if top else None

        return result
