"""Dashboard endpoints: project summary and feature progress."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB

router = APIRouter(prefix="/projects/{project_id}/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    db: ProjectDB,
) -> dict[str, Any]:
    """Aggregated project summary: feature stats, session counts, cost total."""
    backlog_stats, cost_summary = await asyncio.gather(
        asyncio.to_thread(db.backlog.get_stats),
        asyncio.to_thread(db.cost_events.summary),
    )
    sessions = await asyncio.to_thread(db.sessions.list_sessions, limit=1)
    # list_sessions returns a list; we only need the count indicator
    return {
        "features": backlog_stats,
        "cost": cost_summary,
        "has_sessions": len(sessions) > 0,
    }


@router.get("/progress")
async def feature_progress(
    db: ProjectDB,
) -> dict[str, Any]:
    """Feature status breakdown for progress tracking."""
    stats = await asyncio.to_thread(db.backlog.get_stats)
    # get_stats returns counts keyed by status (backlog, planned, in_progress, etc.)
    feature_stats = {
        k: v
        for k, v in stats.items()
        if k
        in {"total", "backlog", "planned", "in_progress", "review", "blocked", "done", "failed"}
    }
    total = feature_stats.get("total", 0)
    done = feature_stats.get("done", 0)
    return {
        "breakdown": feature_stats,
        "completion_pct": round((done / total) * 100, 1) if total > 0 else 0.0,
    }
