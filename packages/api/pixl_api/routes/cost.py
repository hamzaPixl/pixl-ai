"""Cost endpoints: summary, by-model, by-session breakdowns."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.schemas.cost import (
    CostByModelResponse,
    CostBySessionResponse,
    CostSummaryResponse,
)

router = APIRouter(prefix="/projects/{project_id}/cost", tags=["cost"])


@router.get("/summary", response_model=CostSummaryResponse)
async def cost_summary(
    db: ProjectDB,
) -> dict[str, Any]:
    """Get overall cost summary across all sessions."""
    return await asyncio.to_thread(db.cost_events.summary)


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
