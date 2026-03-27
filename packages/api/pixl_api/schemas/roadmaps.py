"""Pydantic request/response models for roadmap endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class CreateRoadmapRequest(BaseModel):
    """Create a new roadmap."""

    title: str
    original_prompt: str = ""
    status: str = "drafting"


class UpdateRoadmapRequest(BaseModel):
    """Partial update of an existing roadmap."""

    title: str | None = None
    original_prompt: str | None = None


class RoadmapResponse(BaseModel):
    """Roadmap detail response."""

    id: str
    title: str
    status: str = "drafting"
    original_prompt: str = ""
    created_at: str | None = None
    updated_at: str | None = None
