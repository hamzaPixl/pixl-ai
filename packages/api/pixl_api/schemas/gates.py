"""Pydantic request/response models for gate endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class GateResponse(BaseModel):
    """A gate node instance within a session."""

    id: str
    session_id: str
    node_id: str
    status: str
    requested_at: str | None = None


class GateActionRequest(BaseModel):
    """Request body for gate approve/reject actions."""

    note: str | None = None
