"""Pydantic request/response models for event endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EventResponse(BaseModel):
    """Single event record."""

    id: int
    event_type: str
    session_id: str | None = None
    node_id: str | None = None
    timestamp: str | None = None
    data: dict[str, Any] | None = None


class EventCountsResponse(BaseModel):
    """Aggregated event counts by type."""

    counts: dict[str, int]
