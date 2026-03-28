"""Budget endpoints: get/set budget config, unpause, cost breakdown."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB

router = APIRouter(prefix="/projects/{project_id}/budget", tags=["budget"])


@router.get("")
async def get_budget(db: ProjectDB) -> dict[str, Any]:
    """Get budget configuration and current spend."""
    try:
        monthly_usd = await asyncio.to_thread(
            db.config.get,  # type: ignore[attr-defined]
            "budget_monthly_usd",  # type: ignore[attr-defined]
        )
    except Exception:
        monthly_usd = None

    cost_summary = await asyncio.to_thread(db.cost_events.summary)
    return {
        "monthly_usd": float(monthly_usd) if monthly_usd else None,
        "current_spend_usd": cost_summary.get("total_cost_usd", 0),
        "is_paused": False,
    }


@router.put("")
async def update_budget(db: ProjectDB, body: dict[str, Any]) -> dict[str, Any]:
    """Set monthly budget limit."""
    monthly_usd = body.get("monthly_usd")
    try:
        await asyncio.to_thread(
            db.config.set,  # type: ignore[attr-defined]
            "budget_monthly_usd",
            str(monthly_usd),  # type: ignore[attr-defined]
        )
    except Exception:
        pass
    return {
        "monthly_usd": monthly_usd,
        "is_paused": False,
    }


@router.post("/unpause")
async def unpause_budget(db: ProjectDB) -> dict[str, Any]:
    """Unpause sessions that were paused due to budget limits."""
    sessions = await asyncio.to_thread(db.sessions.list_sessions, status="budget_paused", limit=100)
    unpaused = []
    for s in sessions:
        sid = s.get("id", "")
        await asyncio.to_thread(db.sessions.update_session, sid, status="running")
        unpaused.append(sid)
    return {"unpaused_sessions": unpaused, "count": len(unpaused)}


@router.get("/costs")
async def budget_costs(
    db: ProjectDB,
    session_id: str | None = Query(None, description="Filter by session ID"),
) -> dict[str, Any]:
    """Get cost breakdown for budget tracking."""
    summary = await asyncio.to_thread(db.cost_events.summary)
    by_model = await asyncio.to_thread(db.cost_events.breakdown_by_model, session_id=session_id)
    return {
        "totals": summary,
        "by_model": by_model,
    }
