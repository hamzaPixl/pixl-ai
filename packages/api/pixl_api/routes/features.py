"""Feature endpoints: CRUD, status transitions, and notes."""

from __future__ import annotations

import asyncio
from typing import Any

from pixl_api.deps import ProjectDB
from pixl_api.helpers import get_or_404
from pixl_api.routes._crud import FilterParam, make_crud_router
from pixl_api.schemas.features import CreateFeatureRequest, UpdateFeatureRequest

router = make_crud_router(
    prefix="/projects/{project_id}/features",
    tag="features",
    entity_name="feature",
    entity_id_param="feature_id",
    list_method="list_features",
    get_method="get_feature",
    create_method="add_feature",
    update_method="update_feature",
    remove_method="remove_feature",
    create_schema=CreateFeatureRequest,
    update_schema=UpdateFeatureRequest,
    list_filters=[
        FilterParam(name="epic_id", description="Filter by epic ID"),
        FilterParam(name="priority", description="Filter by priority"),
        FilterParam(name="feature_type", description="Filter by type"),
    ],
)


# -- Custom endpoint: notes -------------------------------------------------


@router.post("/{feature_id}/notes")
async def add_feature_note(
    db: ProjectDB,
    feature_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Add a note to a feature."""
    feature = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    get_or_404(feature, "feature", feature_id)
    note = body.get("note", "")
    await asyncio.to_thread(db.backlog.add_note, "feature", feature_id, note)
    updated = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    return get_or_404(updated, "feature", feature_id)
