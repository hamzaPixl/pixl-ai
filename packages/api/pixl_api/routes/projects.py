"""Project endpoints: list, create, get, delete, init."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.auth.dependencies import CurrentUser
from pixl_api.errors import EntityNotFoundError
from pixl_api.schemas.projects import CreateProjectRequest, InitProjectRequest, ProjectResponse

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(info: dict[str, Any]) -> dict[str, Any]:
    """Map engine project info dict to API response shape."""
    return {
        "id": info.get("project_id", ""),
        "name": info.get("project_name", ""),
        "description": info.get("description", ""),
        "path": info.get("project_root") or info.get("storage_dir", ""),
        "created_at": info.get("created_at"),
    }


@router.get("", response_model=list[ProjectResponse])
async def list_projects(user: CurrentUser) -> list[dict[str, Any]]:
    """List all known projects."""
    from pixl.projects.registry import list_projects as _list_projects

    projects = await asyncio.to_thread(_list_projects)
    return [_to_response(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: CreateProjectRequest, user: CurrentUser) -> dict[str, Any]:
    """Create a new project in the global workspace."""
    from pixl.projects.registry import create_project as _create_project

    info = await asyncio.to_thread(
        _create_project,
        name=body.name,
        description=body.description,
        project_root=body.project_root,
    )
    return _to_response(info)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: CurrentUser) -> dict[str, Any]:
    """Get project details by ID."""
    from pixl.projects.registry import get_project as _get_project

    info = await asyncio.to_thread(_get_project, project_id)
    if info is None:
        raise EntityNotFoundError("project", project_id)
    return _to_response(info)


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: CurrentUser) -> dict[str, bool]:
    """Delete a project from the global workspace."""
    from pixl.projects.registry import delete_project as _delete_project

    deleted = await asyncio.to_thread(_delete_project, project_id)
    if not deleted:
        raise EntityNotFoundError("project", project_id)
    return {"ok": True}


@router.post("/{project_id}/init", response_model=ProjectResponse)
async def init_project(
    project_id: str, body: InitProjectRequest, user: CurrentUser
) -> dict[str, Any]:
    """Initialize .pixl/ directory for an existing project."""
    from pathlib import Path

    from pixl.projects.registry import ensure_project_config
    from pixl.projects.registry import get_project as _get_project

    info = await asyncio.to_thread(_get_project, project_id)
    if info is None:
        raise EntityNotFoundError("project", project_id)

    project_root = info.get("project_root")
    if not project_root:
        raise EntityNotFoundError("project", project_id)

    await asyncio.to_thread(ensure_project_config, Path(project_root))

    # Re-read after init
    updated = await asyncio.to_thread(_get_project, project_id)
    if updated is None:
        raise EntityNotFoundError("project", project_id)
    return _to_response(updated)
