"""Feature endpoints: CRUD and status transitions."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.errors import EntityNotFoundError, InvalidTransitionError
from pixl_api.helpers import get_or_404
from pixl_api.schemas.features import (
    CreateFeatureRequest,
    FeatureResponse,
    TransitionRequest,
    TransitionResponse,
    UpdateFeatureRequest,
)

router = APIRouter(prefix="/projects/{project_id}/features", tags=["features"])


@router.get("", response_model=list[FeatureResponse])
async def list_features(
    db: ProjectDB,
    status: str | None = Query(None, description="Filter by status"),
    epic_id: str | None = Query(None, description="Filter by epic ID"),
    priority: str | None = Query(None, description="Filter by priority"),
    feature_type: str | None = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[dict[str, Any]]:
    """List features with optional filters."""
    results = await asyncio.to_thread(
        db.backlog.list_features,
        status=status,
        epic_id=epic_id,
        priority=priority,
        feature_type=feature_type,
    )
    return results[offset : offset + limit]


@router.post("", response_model=FeatureResponse, status_code=201)
async def create_feature(
    db: ProjectDB,
    body: CreateFeatureRequest,
) -> dict[str, Any]:
    """Create a new feature."""
    return await asyncio.to_thread(
        db.backlog.add_feature,
        title=body.title,
        description=body.description,
        feature_type=body.feature_type,
        priority=body.priority,
        epic_id=body.epic_id,
        acceptance_criteria=body.acceptance_criteria,
    )


@router.get("/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    db: ProjectDB,
    feature_id: str,
) -> dict[str, Any]:
    """Get a single feature by ID."""
    feature = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    return get_or_404(feature, "feature", feature_id)


@router.put("/{feature_id}", response_model=FeatureResponse)
async def update_feature(
    db: ProjectDB,
    feature_id: str,
    body: UpdateFeatureRequest,
) -> dict[str, Any]:
    """Update an existing feature."""
    feature = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    get_or_404(feature, "feature", feature_id)

    fields = body.model_dump(exclude_none=True)
    if fields:
        await asyncio.to_thread(db.backlog.update_feature, feature_id, **fields)

    updated = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    return get_or_404(updated, "feature", feature_id)


@router.delete("/{feature_id}", status_code=204)
async def delete_feature(
    db: ProjectDB,
    feature_id: str,
) -> None:
    """Delete a feature."""
    feature = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    get_or_404(feature, "feature", feature_id)
    await asyncio.to_thread(db.backlog.remove_feature, feature_id)


@router.post("/{feature_id}/transition", response_model=TransitionResponse)
async def transition_feature(
    db: ProjectDB,
    feature_id: str,
    body: TransitionRequest,
) -> dict[str, Any]:
    """Transition a feature to a new status."""
    feature = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    get_or_404(feature, "feature", feature_id)

    old_status = feature["status"]  # type: ignore[index]

    try:
        from pixl.state.engine import TransitionEngine

        engine = TransitionEngine.default(db.backlog)
        result = await asyncio.to_thread(
            engine.transition, feature_id, body.to_status, note=body.reason
        )
        if not result.success:
            raise InvalidTransitionError(
                "feature", feature_id, result.error or "Transition not allowed"
            )
        return {"old_status": old_status, "new_status": body.to_status}
    except ImportError:
        updated = await asyncio.to_thread(
            db.backlog.update_feature_status,
            feature_id,
            body.to_status,
            note=body.reason,
        )
        if updated is None:
            raise EntityNotFoundError("feature", feature_id)
        return {"old_status": old_status, "new_status": body.to_status}
