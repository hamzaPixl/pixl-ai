"""Pydantic request/response models for feature endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class CreateFeatureRequest(BaseModel):
    """Create a new feature."""

    title: str
    description: str = ""
    feature_type: str = "feature"
    priority: str = "P2"
    epic_id: str | None = None
    acceptance_criteria: list[str] | None = None


class UpdateFeatureRequest(BaseModel):
    """Partial update of an existing feature."""

    title: str | None = None
    description: str | None = None
    priority: str | None = None
    acceptance_criteria: list[str] | None = None


class FeatureResponse(BaseModel):
    """Feature detail response."""

    id: str
    title: str
    description: str = ""
    status: str = "backlog"
    priority: str = "P2"
    type: str = "feature"
    epic_id: str | None = None
    roadmap_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TransitionRequest(BaseModel):
    """Request a status transition."""

    to_status: str
    reason: str | None = None


class TransitionResponse(BaseModel):
    """Result of a status transition."""

    old_status: str
    new_status: str
