"""Pydantic request/response models for session endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class NodeInstanceResponse(BaseModel):
    """Single node instance within a session."""

    model_config = {"extra": "allow"}

    node_id: str
    session_id: str = ""
    state: str = ""
    started_at: str | None = None
    ended_at: str | None = None
    error_message: str | None = None
    output: dict | None = None


class SessionListEntry(BaseModel):
    """Summary view of a session for list responses."""

    model_config = {"extra": "allow"}

    id: str
    status: str
    feature_id: str | None = None
    entity_kind: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class SessionDetail(BaseModel):
    """Full session detail including node instances."""

    model_config = {"extra": "allow"}

    id: str
    status: str
    feature_id: str | None = None
    node_instances: dict[str, NodeInstanceResponse] = {}
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
