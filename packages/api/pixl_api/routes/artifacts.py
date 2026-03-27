"""Artifact endpoints: list, search, create, get, versions."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.helpers import get_or_404
from pixl_api.schemas.artifacts import (
    ArtifactContentResponse,
    ArtifactResponse,
    CreateArtifactRequest,
)

router = APIRouter(prefix="/projects/{project_id}/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactResponse])
async def list_artifacts(
    db: ProjectDB,
    session_id: str | None = Query(None, description="Filter by session ID"),
    type: str | None = Query(None, description="Filter by artifact type"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[dict[str, Any]]:
    """List artifacts with optional filters."""
    if type:
        return await asyncio.to_thread(db.artifacts.list_by_type, type)
    return await asyncio.to_thread(
        db.artifacts.list_page, session_id=session_id or "", limit=limit, offset=offset
    )


@router.get("/search", response_model=list[ArtifactResponse])
async def search_artifacts(
    db: ProjectDB,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    type: str | None = Query(None, description="Filter by artifact type"),
) -> list[dict[str, Any]]:
    """Full-text search across artifacts."""
    return await asyncio.to_thread(db.artifacts.search, q, limit=limit, artifact_type=type)


@router.post("", response_model=ArtifactContentResponse, status_code=201)
async def create_artifact(
    db: ProjectDB,
    body: CreateArtifactRequest,
) -> dict[str, Any]:
    """Create a new artifact."""
    return await asyncio.to_thread(
        db.artifacts.put,
        session_id=body.session_id,
        logical_path=body.logical_path,
        content=body.content,
        artifact_type=body.artifact_type,
        tags=body.tags,
    )


@router.get("/{artifact_id}", response_model=ArtifactContentResponse)
async def get_artifact(
    db: ProjectDB,
    artifact_id: str,
) -> dict[str, Any]:
    """Get a single artifact with content."""
    artifact = await asyncio.to_thread(db.artifacts.get, artifact_id)
    return get_or_404(artifact, "artifact", artifact_id)


@router.get("/{artifact_id}/versions", response_model=list[ArtifactResponse])
async def list_artifact_versions(
    db: ProjectDB,
    artifact_id: str,
) -> list[dict[str, Any]]:
    """List all versions of an artifact."""
    return await asyncio.to_thread(db.artifacts.get_versions, artifact_id)
