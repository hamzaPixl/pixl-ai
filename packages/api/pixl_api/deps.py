"""Core DI layer for project-scoped operations.

Provides FastAPI dependencies for accessing project storage via the
connection pool. Re-exports CurrentUser from auth for convenience.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi import Path as PathParam
from pixl.projects.registry import get_project
from pixl.storage.db.connection import PixlDB

from pixl_api.auth.dependencies import CurrentUser
from pixl_api.errors import EntityNotFoundError
from pixl_api.pool import ProjectDBPool

__all__ = [
    "CurrentUser",
    "ProjectDB",
    "ProjectId",
    "ProjectPath",
    "ProjectRoot",
    "get_pool",
    "get_project_db",
]


def get_pool(request: Request) -> ProjectDBPool:
    """Retrieve the ProjectDBPool singleton from app state."""
    return request.app.state.pool


def _require_project(project_id: str) -> dict[str, Any]:
    """Look up a project by ID or raise EntityNotFoundError."""
    info = get_project(project_id)
    if info is None:
        raise EntityNotFoundError("project", project_id)
    return info


def get_project_db(
    project_id: Annotated[str, PathParam(description="Project identifier")],
    pool: ProjectDBPool = Depends(get_pool),
) -> PixlDB:
    """Resolve PixlDB for the given project from the pool."""
    _require_project(project_id)
    return pool.get(project_id)


def get_project_id(
    project_id: Annotated[str, PathParam(description="Project identifier")],
) -> str:
    """Validate and return project_id from path."""
    _require_project(project_id)
    return project_id


def get_project_path(
    project_id: Annotated[str, PathParam(description="Project identifier")],
) -> Path:
    """Return the project storage path."""
    info = _require_project(project_id)
    storage_dir = info.get("storage_dir")
    if not storage_dir:
        raise ValueError(f"No storage_dir for project: {project_id}")
    return Path(storage_dir)


def get_project_root(
    project_id: Annotated[str, PathParam(description="Project identifier")],
) -> Path:
    """Return the project root path (where .pixl/ lives).

    Falls back to storage_dir if project_root is not set.
    """
    info = _require_project(project_id)
    root = info.get("project_root")
    if root:
        return Path(root)
    storage_dir = info.get("storage_dir")
    if not storage_dir:
        raise ValueError(f"No path for project: {project_id}")
    return Path(storage_dir)


# Type aliases for clean route signatures
ProjectDB = Annotated[PixlDB, Depends(get_project_db)]
ProjectId = Annotated[str, Depends(get_project_id)]
ProjectPath = Annotated[Path, Depends(get_project_path)]
ProjectRoot = Annotated[Path, Depends(get_project_root)]
