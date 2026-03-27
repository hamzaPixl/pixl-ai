"""Pydantic request/response models for artifact endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateArtifactRequest(BaseModel):
    """Request body for creating an artifact."""

    session_id: str
    logical_path: str
    content: str | None = None
    artifact_type: str = "other"
    tags: list[str] | None = None


class ArtifactResponse(BaseModel):
    """Summary view of an artifact (no content)."""

    id: str
    session_id: str | None = None
    logical_path: str | None = Field(None, alias="path")
    artifact_type: str | None = Field(None, alias="type")
    version: str | None = None
    created_at: str | None = None
    tags: list[str] | None = None
    name: str | None = None

    model_config = {"populate_by_name": True}


class ArtifactContentResponse(BaseModel):
    """Full artifact including content."""

    id: str
    content: str | None = None
    logical_path: str | None = Field(None, alias="path")
    artifact_type: str | None = Field(None, alias="type")
    name: str | None = None
    version: str | None = None
    created_at: str | None = None

    model_config = {"populate_by_name": True}
