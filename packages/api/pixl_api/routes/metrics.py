"""Metrics endpoints: agent performance and session metrics."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB

router = APIRouter(prefix="/projects/{project_id}/metrics", tags=["metrics"])


@router.get("/agents")
async def all_agent_metrics(
    db: ProjectDB,
    timeframe_hours: int | None = None,
) -> dict[str, Any]:
    """Get performance metrics for all agents."""
    agents = await asyncio.to_thread(db.metrics.get_all_agent_performance, timeframe_hours)
    return {"agents": agents, "timeframe_hours": timeframe_hours}


@router.get("/agents/{agent_name}")
async def agent_performance(
    db: ProjectDB,
    agent_name: str,
    timeframe_hours: int | None = None,
) -> dict[str, Any]:
    """Get performance metrics for a specific agent."""
    return await asyncio.to_thread(db.metrics.get_agent_performance, agent_name, timeframe_hours)


@router.get("/sessions/{session_id}")
async def session_metrics(
    db: ProjectDB,
    session_id: str,
) -> list[dict[str, Any]]:
    """Get all agent metrics for a workflow session."""
    metrics_list = await asyncio.to_thread(db.metrics.get_session_metrics, session_id)
    return [
        {
            "agent_name": m.agent_name,
            "model_name": m.model_name,
            "session_id": m.session_id,
            "node_id": m.node_id,
            "feature_id": m.feature_id,
            "started_at": m.started_at.isoformat(),
            "completed_at": m.completed_at.isoformat() if m.completed_at else None,
            "input_tokens": m.input_tokens,
            "output_tokens": m.output_tokens,
            "total_tokens": m.total_tokens,
            "total_cost_usd": m.total_cost_usd,
            "success": m.success,
            "error_type": m.error_type,
            "error_message": m.error_message,
        }
        for m in metrics_list
    ]
