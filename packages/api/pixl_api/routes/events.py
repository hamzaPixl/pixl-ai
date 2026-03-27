"""Event endpoints: list events, event counts."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.schemas.events import EventCountsResponse, EventResponse

router = APIRouter(prefix="/projects/{project_id}/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
async def list_events(
    db: ProjectDB,
    session_id: str | None = Query(None, description="Filter by session ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[dict[str, Any]]:
    """List events for a project, optionally filtered by session or type."""
    rows = await asyncio.to_thread(
        db.events.get_events,
        session_id=session_id,
        event_type=event_type,
        limit=limit,
    )
    # Apply offset manually since the protocol does not support it
    return rows[offset:]


@router.get("/counts", response_model=EventCountsResponse)
async def event_counts(
    db: ProjectDB,
    session_id: str | None = Query(None, description="Filter by session ID"),
    since: str | None = Query(None, description="ISO timestamp to filter from"),
) -> EventCountsResponse:
    """Get event counts grouped by event type."""
    counts = await asyncio.to_thread(
        db.events.get_event_counts,
        session_id=session_id,
        since=since,
    )
    return EventCountsResponse(counts=counts)
