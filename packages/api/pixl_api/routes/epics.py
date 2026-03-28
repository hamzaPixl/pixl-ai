"""Epic endpoints: CRUD, status transitions, and child features."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.errors import EntityNotFoundError, InvalidTransitionError
from pixl_api.helpers import get_or_404
from pixl_api.schemas.epics import CreateEpicRequest, UpdateEpicRequest
from pixl_api.schemas.features import TransitionRequest

router = APIRouter(prefix="/projects/{project_id}/epics", tags=["epics"])


@router.get(
    "",
)
async def list_epics(
    db: ProjectDB,
    status: str | None = Query(None, description="Filter by status"),
    roadmap_id: str | None = Query(None, description="Filter by roadmap ID"),
) -> list[dict[str, Any]]:
    """List epics with optional filters."""
    return await asyncio.to_thread(
        db.backlog.list_epics,
        status=status,
        roadmap_id=roadmap_id,
    )


@router.post("", status_code=201)
async def create_epic(
    db: ProjectDB,
    body: CreateEpicRequest,
) -> dict[str, Any]:
    """Create a new epic."""
    return await asyncio.to_thread(
        db.backlog.add_epic,
        title=body.title,
        original_prompt=body.original_prompt,
        workflow_id=body.workflow_id,
        outcome=body.outcome,
        kpis=body.kpis,
        roadmap_id=body.roadmap_id,
        status=body.status,
    )


@router.get(
    "/{epic_id}",
)
async def get_epic(
    db: ProjectDB,
    epic_id: str,
) -> dict[str, Any]:
    """Get a single epic by ID."""
    epic = await asyncio.to_thread(db.backlog.get_epic, epic_id)
    return get_or_404(epic, "epic", epic_id)


@router.put(
    "/{epic_id}",
)
@router.patch(
    "/{epic_id}",
)
async def update_epic(
    db: ProjectDB,
    epic_id: str,
    body: UpdateEpicRequest,
) -> dict[str, Any]:
    """Update an existing epic."""
    epic = await asyncio.to_thread(db.backlog.get_epic, epic_id)
    get_or_404(epic, "epic", epic_id)

    fields = body.model_dump(exclude_none=True)
    if fields:
        await asyncio.to_thread(db.backlog.update_epic, epic_id, **fields)

    updated = await asyncio.to_thread(db.backlog.get_epic, epic_id)
    return get_or_404(updated, "epic", epic_id)


@router.delete("/{epic_id}")
async def delete_epic(
    db: ProjectDB,
    epic_id: str,
) -> dict[str, bool]:
    """Delete an epic."""
    epic = await asyncio.to_thread(db.backlog.get_epic, epic_id)
    get_or_404(epic, "epic", epic_id)
    await asyncio.to_thread(db.backlog.remove_epic, epic_id)
    return {"deleted": True}


@router.post(
    "/{epic_id}/transition",
)
async def transition_epic(
    db: ProjectDB,
    epic_id: str,
    body: TransitionRequest,
) -> dict[str, Any]:
    """Transition an epic to a new status."""
    epic = await asyncio.to_thread(db.backlog.get_epic, epic_id)
    get_or_404(epic, "epic", epic_id)

    old_status = epic["status"]  # type: ignore[index]

    try:
        from pixl.state.engine import TransitionEngine

        engine = TransitionEngine.default(db.backlog)
        result = await asyncio.to_thread(
            engine.transition, epic_id, body.to_status, note=body.reason
        )
        if not result.success:
            raise InvalidTransitionError("epic", epic_id, result.error or "Transition not allowed")
        return {"old_status": old_status, "new_status": body.to_status}
    except ImportError:
        updated = await asyncio.to_thread(
            db.backlog.update_epic_status,
            epic_id,
            body.to_status,
            note=body.reason,
        )
        if updated is None:
            raise EntityNotFoundError("epic", epic_id)
        return {"old_status": old_status, "new_status": body.to_status}


@router.get(
    "/{epic_id}/features",
)
async def list_epic_features(
    db: ProjectDB,
    epic_id: str,
) -> list[dict[str, Any]]:
    """List all features belonging to an epic."""
    epic = await asyncio.to_thread(db.backlog.get_epic, epic_id)
    get_or_404(epic, "epic", epic_id)

    return await asyncio.to_thread(
        db.backlog.list_features,
        epic_id=epic_id,
    )


@router.get("/{epic_id}/history")
async def epic_history(
    db: ProjectDB,
    epic_id: str,
) -> list[dict[str, Any]]:
    """Get state transition history for an epic."""
    return await asyncio.to_thread(db.events.get_entity_history, epic_id)


@router.get("/{epic_id}/transitions")
async def epic_transitions(
    db: ProjectDB,
    epic_id: str,
) -> list[dict[str, Any]]:
    """Get state transitions for an epic."""
    return await asyncio.to_thread(db.events.get_history, "epic", epic_id)
