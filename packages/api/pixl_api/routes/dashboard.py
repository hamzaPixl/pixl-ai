"""Dashboard endpoints: project summary and feature progress."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/dashboard", tags=["dashboard"])


def _projection_store(db: ProjectDB):  # noqa: ANN202
    """Instantiate ProjectionStore from the project database."""
    from pixl.storage.db.projections import ProjectionStore

    return ProjectionStore(db)


async def _build_overview(db: ProjectDB) -> dict[str, Any]:
    """Build full DashboardOverview matching the Console's expected shape."""
    from pixl.storage.db.projections import ProjectionStore

    store = ProjectionStore(db)

    # Phase 1: independent read-only queries in parallel
    factory, stats, cost_summary, active_sessions, recent_sessions = await asyncio.gather(
        asyncio.to_thread(store.factory_home),
        asyncio.to_thread(db.backlog.get_stats),
        asyncio.to_thread(db.cost_events.summary),
        asyncio.to_thread(db.sessions.get_active_sessions),
        asyncio.to_thread(db.sessions.get_recent_sessions, 10),  # type: ignore[attr-defined]
    )

    # Phase 2: secondary queries in parallel
    recent_events, breakdown_rows, incidents_result = await asyncio.gather(
        _safe_get_events(db),
        _safe_breakdown_by_model(db),
        _safe_get_incidents(db),
    )

    # Feature completion
    feat = stats.get("features", {})
    total = feat.get("total", 0)
    done = feat.get("done", 0)
    completion_pct = round((done / total) * 100, 1) if total > 0 else 0.0

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
    for row in breakdown_rows:
        cost["by_model"][row.get("model", "unknown")] = row.get("total_cost_usd", 0)

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
    recovery = _build_recovery(incidents_result)

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


async def _safe_get_events(db: ProjectDB) -> list[dict[str, Any]]:
    """Fetch recent events, returning empty list on failure."""
    try:
        return await asyncio.to_thread(db.events.get_events, limit=20)
    except Exception as e:
        logger.warning("Failed to fetch recent events: %s", e)
        return []


async def _safe_breakdown_by_model(db: ProjectDB) -> list[dict[str, Any]]:
    """Fetch cost breakdown by model, returning empty list on failure."""
    try:
        return await asyncio.to_thread(db.cost_events.breakdown_by_model)
    except Exception as e:
        logger.warning("Failed to fetch cost breakdown by model: %s", e)
        return []


async def _safe_get_incidents(db: ProjectDB) -> list[dict[str, Any]]:
    """Fetch recent incidents, returning empty list on failure."""
    try:
        incidents = await asyncio.to_thread(db.incidents.list_recent, limit=100)
        return [i.to_dict() if hasattr(i, "to_dict") else i for i in incidents]
    except Exception as e:
        logger.warning("Failed to fetch recovery incidents: %s", e)
        return []


def _build_recovery(inc_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Build recovery stats from a list of incident dicts."""
    if not inc_list:
        return {
            "total_incidents": 0,
            "succeeded": 0,
            "failed": 0,
            "escalated": 0,
            "success_rate": 0,
            "top_errors": [],
        }
    succeeded = sum(1 for i in inc_list if i.get("outcome") == "succeeded")
    failed_inc = sum(1 for i in inc_list if i.get("outcome") == "failed")
    escalated = sum(1 for i in inc_list if i.get("outcome") == "escalated")
    return {
        "total_incidents": len(inc_list),
        "succeeded": succeeded,
        "failed": failed_inc,
        "escalated": escalated,
        "success_rate": round(succeeded / len(inc_list) * 100, 1) if inc_list else 0,
        "top_errors": [],
    }


@router.get("/overview")
async def dashboard_overview(
    db: ProjectDB,
) -> dict[str, Any]:
    """Full operational overview matching the Console DashboardOverview type."""
    return await _build_overview(db)


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
