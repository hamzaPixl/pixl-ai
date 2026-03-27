"""Roadmap endpoints: CRUD and status transitions."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.errors import EntityNotFoundError, InvalidTransitionError
from pixl_api.helpers import get_or_404
from pixl_api.schemas.features import TransitionRequest, TransitionResponse
from pixl_api.schemas.roadmaps import CreateRoadmapRequest, RoadmapResponse, UpdateRoadmapRequest

router = APIRouter(prefix="/projects/{project_id}/roadmaps", tags=["roadmaps"])


@router.get("", response_model=list[RoadmapResponse])
async def list_roadmaps(
    db: ProjectDB,
    status: str | None = Query(None, description="Filter by status"),
) -> list[dict[str, Any]]:
    """List roadmaps with optional status filter."""
    return await asyncio.to_thread(
        db.backlog.list_roadmaps,
        status=status,
    )


@router.post("", response_model=RoadmapResponse, status_code=201)
async def create_roadmap(
    db: ProjectDB,
    body: CreateRoadmapRequest,
) -> dict[str, Any]:
    """Create a new roadmap."""
    return await asyncio.to_thread(
        db.backlog.add_roadmap,
        title=body.title,
        original_prompt=body.original_prompt,
        status=body.status,
    )


@router.get("/{roadmap_id}", response_model=RoadmapResponse)
async def get_roadmap(
    db: ProjectDB,
    roadmap_id: str,
) -> dict[str, Any]:
    """Get a single roadmap by ID."""
    roadmap = await asyncio.to_thread(db.backlog.get_roadmap, roadmap_id)
    return get_or_404(roadmap, "roadmap", roadmap_id)


@router.put("/{roadmap_id}", response_model=RoadmapResponse)
async def update_roadmap(
    db: ProjectDB,
    roadmap_id: str,
    body: UpdateRoadmapRequest,
) -> dict[str, Any]:
    """Update an existing roadmap."""
    roadmap = await asyncio.to_thread(db.backlog.get_roadmap, roadmap_id)
    get_or_404(roadmap, "roadmap", roadmap_id)

    fields = body.model_dump(exclude_none=True)
    if fields:
        await asyncio.to_thread(db.backlog.update_roadmap, roadmap_id, **fields)

    updated = await asyncio.to_thread(db.backlog.get_roadmap, roadmap_id)
    return get_or_404(updated, "roadmap", roadmap_id)


@router.post("/{roadmap_id}/transition", response_model=TransitionResponse)
async def transition_roadmap(
    db: ProjectDB,
    roadmap_id: str,
    body: TransitionRequest,
) -> dict[str, Any]:
    """Transition a roadmap to a new status."""
    roadmap = await asyncio.to_thread(db.backlog.get_roadmap, roadmap_id)
    get_or_404(roadmap, "roadmap", roadmap_id)

    old_status = roadmap["status"]  # type: ignore[index]

    try:
        from pixl.state.engine import TransitionEngine

        engine = TransitionEngine.default(db.backlog)
        result = await asyncio.to_thread(
            engine.transition, roadmap_id, body.to_status, note=body.reason
        )
        if not result.success:
            raise InvalidTransitionError(
                "roadmap", roadmap_id, result.error or "Transition not allowed"
            )
        return {"old_status": old_status, "new_status": body.to_status}
    except ImportError:
        updated = await asyncio.to_thread(
            db.backlog.update_roadmap_status,
            roadmap_id,
            body.to_status,
            note=body.reason,
        )
        if updated is None:
            raise EntityNotFoundError("roadmap", roadmap_id)
        return {"old_status": old_status, "new_status": body.to_status}
