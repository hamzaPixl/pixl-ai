"""Roadmap endpoints: CRUD, status transitions, and child epics."""

from __future__ import annotations

import asyncio
from typing import Any

from pixl_api.deps import ProjectDB
from pixl_api.routes._crud import make_crud_router
from pixl_api.schemas.roadmaps import CreateRoadmapRequest, UpdateRoadmapRequest

router = make_crud_router(
    prefix="/projects/{project_id}/roadmaps",
    tag="roadmaps",
    entity_name="roadmap",
    entity_id_param="roadmap_id",
    list_method="list_roadmaps",
    get_method="get_roadmap",
    create_method="add_roadmap",
    update_method="update_roadmap",
    remove_method="remove_roadmap",
    create_schema=CreateRoadmapRequest,
    update_schema=UpdateRoadmapRequest,
    paginate=False,
)


# -- Custom endpoint: child epics -------------------------------------------


@router.get("/{roadmap_id}/epics")
async def roadmap_epics(
    db: ProjectDB,
    roadmap_id: str,
) -> list[dict[str, Any]]:
    """List epics belonging to a roadmap."""
    return await asyncio.to_thread(db.backlog.list_epics, roadmap_id=roadmap_id)
