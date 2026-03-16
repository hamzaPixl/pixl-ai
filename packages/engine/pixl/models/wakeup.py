"""Wakeup request model — serialized session triggers with coalescing.

All session-resuming actions (start, resume, retry, gate_approved) go
through the wakeup queue instead of directly spawning background tasks.
This prevents double-starts and provides per-session locking.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class WakeupReason(StrEnum):
    START = "start"
    RESUME = "resume"
    RETRY = "retry"
    GATE_APPROVED = "gate_approved"
    CHAIN = "chain"
    BUDGET_UNPAUSE = "budget_unpause"


class WakeupStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COALESCED = "coalesced"
    FAILED = "failed"


class WakeupRequest(BaseModel):
    """A queued request to wake up a session."""

    id: int | None = None
    session_id: str
    reason: WakeupReason
    status: WakeupStatus = Field(default=WakeupStatus.PENDING)
    coalesced_count: int = 0
    payload_json: dict | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: datetime | None = None
