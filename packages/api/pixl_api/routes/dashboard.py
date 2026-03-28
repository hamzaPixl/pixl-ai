"""Dashboard endpoints: project summary and feature progress."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB

router = APIRouter(prefix="/projects/{project_id}/dashboard", tags=["dashboard"])


def _projection_store(db: ProjectDB):  # noqa: ANN202
    """Instantiate ProjectionStore from the project database."""
    from pixl.storage.db.projections import ProjectionStore

    return ProjectionStore(db)


def _build_overview(db: ProjectDB) -> dict[str, Any]:
    """Build full DashboardOverview matching the Console's expected shape."""
    from pixl.storage.db.projections import ProjectionStore

    store = ProjectionStore(db)

    # Parallel-safe: all are read-only on the same connection
    factory = store.factory_home()
    stats = db.backlog.get_stats()
    cost_summary = db.cost_events.summary()

    # Feature completion
    feat = stats.get("features", {})
    total = feat.get("total", 0)
    done = feat.get("done", 0)
    completion_pct = round((done / total) * 100, 1) if total > 0 else 0.0

    # Active + recent sessions
    active_sessions = db.sessions.get_active_sessions()
    recent_sessions = db.sessions.get_recent_sessions(limit=10)

    # Recent events
    try:
        recent_events = db.events.get_events(limit=20)
    except Exception:
        recent_events = []

    # Cost breakdown
    cost = {
        "total_cost_usd": cost_summary.get("total_cost_usd", 0),
        "total_tokens": cost_summary.get("total_input_tokens", 0)
        + cost_summary.get("total_output_tokens", 0),
        "input_tokens": cost_summary.get("total_input_tokens", 0),
        "output_tokens": cost_summary.get("total_output_tokens", 0),
        "by_model": {},
        "by_agent": {},
    }
    try:
        for row in db.cost_events.breakdown_by_model():
            cost["by_model"][row.get("model", "unknown")] = row.get("total_cost_usd", 0)
    except Exception:
        pass

    # Timing stats
    total_sessions = len(recent_sessions)
    completed = [s for s in recent_sessions if s.get("status") == "completed"]
    failed = [s for s in recent_sessions if s.get("status") == "failed"]
    durations = [s.get("execution_seconds", 0) for s in completed if s.get("execution_seconds")]
    timing = {
        "total_sessions": total_sessions,
        "completed_sessions": len(completed),
        "failed_sessions": len(failed),
        "avg_session_duration_minutes": round(sum(durations) / len(durations) / 60, 1)
        if durations
        else None,
        "median_session_duration_minutes": None,
        "avg_stage_duration_seconds": None,
        "fastest_session_minutes": round(min(durations) / 60, 1) if durations else None,
        "slowest_session_minutes": round(max(durations) / 60, 1) if durations else None,
    }

    # Recovery
    try:
        incidents = db.incidents.list_recent(limit=100)
        inc_list = [i.to_dict() if hasattr(i, "to_dict") else i for i in incidents]
        succeeded = sum(1 for i in inc_list if i.get("outcome") == "succeeded")
        failed_inc = sum(1 for i in inc_list if i.get("outcome") == "failed")
        escalated = sum(1 for i in inc_list if i.get("outcome") == "escalated")
        recovery = {
            "total_incidents": len(inc_list),
            "succeeded": succeeded,
            "failed": failed_inc,
            "escalated": escalated,
            "success_rate": round(succeeded / len(inc_list) * 100, 1) if inc_list else 0,
            "top_errors": [],
        }
    except Exception:
        recovery = {
            "total_incidents": 0,
            "succeeded": 0,
            "failed": 0,
            "escalated": 0,
            "success_rate": 0,
            "top_errors": [],
        }

    return {
        "project_name": "",
        "stats": stats,
        "completion_pct": completion_pct,
        "active_sessions": active_sessions,
        "recent_sessions": recent_sessions,
        "recent_events": recent_events,
        "pending_gates": factory.get("pending_gates", []),
        "autonomy": factory.get("autonomy"),
        "chains": None,
        "contracts": None,
        "cost": cost,
        "timing": timing,
        "agents": [],
        "recovery": recovery,
        # Also include factory_home fields for backward compat
        "live_runs": factory.get("live_runs", []),
        "recovering": factory.get("recovering", []),
        "recently_completed": factory.get("recently_completed", []),
        "health": factory.get("health"),
    }


@router.get("/overview")
async def dashboard_overview(
    db: ProjectDB,
) -> dict[str, Any]:
    """Full operational overview matching the Console DashboardOverview type."""
    return await asyncio.to_thread(_build_overview, db)


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
