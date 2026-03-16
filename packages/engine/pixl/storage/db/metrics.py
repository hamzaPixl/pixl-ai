"""Database operations for agent performance metrics."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from pixl.models.metrics import AgentMetrics
from pixl.storage.db.base import BaseStore


class MetricsStore(BaseStore):
    """Storage layer for agent performance metrics."""

    def store_agent_metrics(self, metrics: AgentMetrics) -> str:
        """Store agent metrics and return the created record ID."""
        cursor = self._conn.execute(
            """
            INSERT INTO agent_metrics (
                agent_name, model_name, session_id, node_id, feature_id,
                started_at, completed_at, input_tokens, output_tokens, total_tokens,
                total_cost_usd, success, error_type, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics.agent_name,
                metrics.model_name,
                metrics.session_id,
                metrics.node_id,
                metrics.feature_id,
                metrics.started_at.isoformat(),
                metrics.completed_at.isoformat() if metrics.completed_at else None,
                metrics.input_tokens,
                metrics.output_tokens,
                metrics.total_tokens,
                metrics.total_cost_usd,
                1 if metrics.success else 0,
                metrics.error_type,
                metrics.error_message,
            ),
        )
        self._conn.commit()
        return str(cursor.lastrowid)

    def get_agent_performance(
        self, agent_name: str, timeframe_hours: int | None = None
    ) -> dict[str, Any]:
        """Get performance snapshot for a specific agent."""
        where_clause = "WHERE agent_name = ?"
        params = [agent_name]

        if timeframe_hours:
            where_clause += (
                f" AND datetime(started_at) > datetime('now', '-{timeframe_hours} hours')"
            )

        cursor = self._conn.execute(
            f"""
            SELECT
                COUNT(*) as total_executions,
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                AVG(total_cost_usd) as avg_cost,
                SUM(total_cost_usd) as total_cost,
                AVG(total_tokens) as avg_tokens,
                AVG(
                    CASE
                        WHEN completed_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(started_at)) * 86400
                        ELSE NULL
                    END
                ) as avg_duration_seconds
            FROM agent_metrics
            {where_clause}
            """,
            params,
        )

        row = cursor.fetchone()
        if not row:
            return {}

        return {
            "agent_name": agent_name,
            "total_executions": row[0] or 0,
            "success_rate": row[1] or 0.0,
            "avg_cost_usd": row[2] or 0.0,
            "total_cost_usd": row[3] or 0.0,
            "avg_tokens": row[4] or 0,
            "avg_duration_seconds": row[5] or 0.0,
        }

    def get_session_metrics(self, session_id: str) -> list[AgentMetrics]:
        """Get all agent metrics for a specific workflow session."""
        cursor = self._conn.execute(
            """
            SELECT
                agent_name, model_name, session_id, node_id, feature_id,
                started_at, completed_at, input_tokens, output_tokens, total_tokens,
                total_cost_usd, success, error_type, error_message
            FROM agent_metrics
            WHERE session_id = ?
            ORDER BY started_at
            """,
            (session_id,),
        )

        metrics_list = []
        for row in cursor.fetchall():
            metrics = AgentMetrics(
                agent_name=row[0],
                model_name=row[1],
                session_id=row[2],
                node_id=row[3],
                feature_id=row[4],
                started_at=datetime.fromisoformat(row[5]),
                completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                input_tokens=row[7],
                output_tokens=row[8],
                total_tokens=row[9],
                total_cost_usd=row[10],
                success=bool(row[11]),
                error_type=row[12],
                error_message=row[13],
            )
            metrics_list.append(metrics)

        return metrics_list

    def get_feature_metrics(self, feature_id: str) -> list[AgentMetrics]:
        """Get all agent metrics for a specific feature across all sessions."""
        cursor = self._conn.execute(
            """
            SELECT
                agent_name, model_name, session_id, node_id, feature_id,
                started_at, completed_at, input_tokens, output_tokens, total_tokens,
                total_cost_usd, success, error_type, error_message
            FROM agent_metrics
            WHERE feature_id = ?
            ORDER BY started_at
            """,
            (feature_id,),
        )

        metrics_list = []
        for row in cursor.fetchall():
            metrics = AgentMetrics(
                agent_name=row[0],
                model_name=row[1],
                session_id=row[2],
                node_id=row[3],
                feature_id=row[4],
                started_at=datetime.fromisoformat(row[5]),
                completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                input_tokens=row[7],
                output_tokens=row[8],
                total_tokens=row[9],
                total_cost_usd=row[10],
                success=bool(row[11]),
                error_type=row[12],
                error_message=row[13],
            )
            metrics_list.append(metrics)

        return metrics_list
