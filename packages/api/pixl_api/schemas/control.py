"""Pydantic request/response models for session control endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class ControlResponse(BaseModel):
    """Response for session control actions (pause, resume, cancel, retry)."""

    session_id: str
    status: str
    message: str
