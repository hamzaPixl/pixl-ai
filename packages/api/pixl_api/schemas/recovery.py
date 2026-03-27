"""Pydantic response models for recovery endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BlockedNodeResponse(BaseModel):
    """A node currently blocked and awaiting intervention."""

    session_id: str
    node_id: str
    blocked_reason: str | None = None
    error_message: str | None = None
    failure_kind: str | None = None
    blocked_since: str | None = None
    feature_id: str | None = None
    feature_title: str = ""
    blocker_artifact: str | None = None
    recovery_events: list[dict[str, Any]] = []


class RecoveryActionResponse(BaseModel):
    """Response for a recovery action (retry/skip)."""

    session_id: str
    node_id: str
    action: str
    status: str
    message: str
