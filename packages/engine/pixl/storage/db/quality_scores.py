"""Quality score storage for swarm execution metrics.

Records time-series quality metrics scoped to chains, nodes, sessions,
features, or epics.  Supports trend queries for the dashboard.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from pixl.storage.db.base import BaseStore

_VALID_SCOPE_TYPES = frozenset({"chain", "node", "session", "feature", "epic"})

class QualityScoreDB(BaseStore):
    """CRUD helpers for quality metrics."""

    def record(
        self,
        scope_type: str,
        scope_id: str,
        metric: str,
        value: float,
    ) -> int:
        """Record a quality metric.  Returns the row ID."""
        if scope_type not in _VALID_SCOPE_TYPES:
            msg = f"invalid scope_type: {scope_type}"
            raise ValueError(msg)
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO quality_scores (scope_type, scope_id, metric, value)"
                " VALUES (?, ?, ?, ?)",
                (scope_type, scope_id, metric, value),
            )
            return cur.lastrowid or 0

    def get_scores(
        self,
        scope_type: str,
        scope_id: str,
        *,
        metric: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get quality scores for a scope, optionally filtered by metric."""
        clauses = ["scope_type = ?", "scope_id = ?"]
        params: list[Any] = [scope_type, scope_id]
        if metric:
            clauses.append("metric = ?")
            params.append(metric)
        params.append(limit)
        sql = (
            "SELECT id, scope_type, scope_id, metric, value, measured_at"
            " FROM quality_scores"
            f" WHERE {' AND '.join(clauses)}"
            " ORDER BY measured_at DESC LIMIT ?"
        )
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": r[0],
                "scope_type": r[1],
                "scope_id": r[2],
                "metric": r[3],
                "value": r[4],
                "measured_at": r[5],
            }
            for r in rows
        ]

    def get_trends(
        self,
        scope_type: str,
        scope_id: str,
        metric: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get time-series trend for a metric (oldest first)."""
        sql = (
            "SELECT id, scope_type, scope_id, metric, value, measured_at"
            " FROM quality_scores"
            " WHERE scope_type = ? AND scope_id = ? AND metric = ?"
            " ORDER BY measured_at ASC LIMIT ?"
        )
        rows = self._conn.execute(sql, (scope_type, scope_id, metric, limit)).fetchall()
        return [
            {
                "id": r[0],
                "scope_type": r[1],
                "scope_id": r[2],
                "metric": r[3],
                "value": r[4],
                "measured_at": r[5],
            }
            for r in rows
        ]

    def get_latest_scores(
        self,
        scope_type: str,
        scope_id: str,
    ) -> dict[str, float]:
        """Get most recent value per metric for a scope."""
        sql = (
            "SELECT metric, value FROM quality_scores"
            " WHERE scope_type = ? AND scope_id = ?"
            "   AND id IN ("
            "       SELECT MAX(id) FROM quality_scores"
            "       WHERE scope_type = ? AND scope_id = ?"
            "       GROUP BY metric"
            "   )"
        )
        rows = self._conn.execute(sql, (scope_type, scope_id, scope_type, scope_id)).fetchall()
        return {r[0]: r[1] for r in rows}
