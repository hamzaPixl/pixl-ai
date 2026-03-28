"""Epic endpoints: CRUD, status transitions, and child features."""

from __future__ import annotations

import asyncio
from typing import Any

from pixl_api.deps import ProjectDB
from pixl_api.helpers import get_or_404
from pixl_api.routes._crud import FilterParam, make_crud_router
from pixl_api.schemas.epics import CreateEpicRequest, UpdateEpicRequest

router = make_crud_router(
    prefix="/projects/{project_id}/epics",
    tag="epics",
    entity_name="epic",
    entity_id_param="epic_id",
    list_method="list_epics",
    get_method="get_epic",
    create_method="add_epic",
    update_method="update_epic",
    remove_method="remove_epic",
    create_schema=CreateEpicRequest,
    update_schema=UpdateEpicRequest,
    list_filters=[
        FilterParam(name="roadmap_id", description="Filter by roadmap ID"),
    ],
    paginate=False,
)


# -- Custom endpoint: child features ----------------------------------------


@router.get("/{epic_id}/features")
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
