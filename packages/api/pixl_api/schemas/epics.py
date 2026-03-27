"""Pydantic request/response models for epic endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateEpicRequest(BaseModel):
    """Create a new epic."""

    title: str
    original_prompt: str = ""
    workflow_id: str | None = None
    outcome: str = ""
    kpis: list[dict[str, Any]] | None = None
    roadmap_id: str | None = None
    status: str = "drafting"


class UpdateEpicRequest(BaseModel):
    """Partial update of an existing epic."""

    title: str | None = None
    outcome: str | None = None
    kpis: list[dict[str, Any]] | None = None
    workflow_id: str | None = None


class EpicResponse(BaseModel):
    """Epic detail response."""

    id: str
    title: str
    status: str = "drafting"
    outcome: str = ""
    kpis: list[dict[str, Any]] | None = None
    workflow_id: str | None = None
    roadmap_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
