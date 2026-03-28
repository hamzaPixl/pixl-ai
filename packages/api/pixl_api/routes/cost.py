"""Cost endpoints: summary, by-model, by-session breakdowns."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.schemas.cost import (
    CostByModelResponse,
    CostBySessionResponse,
)

router = APIRouter(prefix="/projects/{project_id}/cost", tags=["cost"])


@router.get("/summary")
async def cost_summary(
    db: ProjectDB,
) -> dict[str, Any]:
    """Get cost summary in the shape the Console expects.

    Returns { totals, by_model[], by_agent[], by_feature[] } so the
    Console does not need client-side dict→array transformation.
    """
    raw_summary, by_model_raw = await asyncio.gather(
        asyncio.to_thread(db.cost_events.summary),
        asyncio.to_thread(db.cost_events.breakdown_by_model),
    )

    totals = {
        "cost_usd": raw_summary.get("total_cost_usd", 0),
        "input_tokens": raw_summary.get("total_input_tokens", 0),
        "output_tokens": raw_summary.get("total_output_tokens", 0),
        "total_tokens": (
            raw_summary.get("total_input_tokens", 0) + raw_summary.get("total_output_tokens", 0)
        ),
    }

    by_model = [
        {
            "model": row.get("model_name", "unknown"),
            "cost_usd": row.get("cost_usd", 0),
            "input_tokens": row.get("input_tokens", 0),
            "output_tokens": row.get("output_tokens", 0),
            "executions": row.get("event_count", 0),
        }
        for row in by_model_raw
    ]

    return {
        "totals": totals,
        "by_model": by_model,
        "by_agent": [],
        "by_feature": [],
    }


@router.get("/by-model", response_model=list[CostByModelResponse])
async def cost_by_model(
    db: ProjectDB,
    session_id: str | None = Query(None, description="Filter by session ID"),
) -> list[dict[str, Any]]:
    """Get cost breakdown grouped by model."""
    return await asyncio.to_thread(db.cost_events.breakdown_by_model, session_id=session_id)


@router.get("/by-session", response_model=list[CostBySessionResponse])
async def cost_by_session(
    db: ProjectDB,
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> list[dict[str, Any]]:
    """Get cost breakdown grouped by session."""
    return await asyncio.to_thread(db.cost_events.total_by_session, limit=limit)
