"""Heartbeat run model — first-class execution windows.

Each run represents a bounded execution period within a session.
Replaces heuristic staleness detection with authoritative liveness
via periodic heartbeat_at updates.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class InvocationSource(StrEnum):
    START = "start"
    RESUME = "resume"
    RETRY = "retry"
    GATE_APPROVED = "gate_approved"
    CHAIN = "chain"


class HeartbeatRun(BaseModel):
    """A single bounded execution window within a workflow session."""

    id: str = Field(description="run-XXXX")
    session_id: str = Field(description="Parent session ID")
    status: RunStatus = Field(default=RunStatus.QUEUED)
    invocation: InvocationSource = Field(default=InvocationSource.START)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    heartbeat_at: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    steps_executed: int = 0
    error_message: str | None = None
    context_snapshot: dict | None = Field(default=None, description="Cursor + baton at run start")
    created_at: datetime = Field(default_factory=datetime.now)

    @staticmethod
    def generate_id() -> str:
        return f"run-{uuid.uuid4().hex[:8]}"

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
        )

    @property
    def is_stalled(self) -> bool:
        """Check if this run has gone silent (no heartbeat in 60s)."""
        if self.status != RunStatus.RUNNING or not self.heartbeat_at:
            return False
        return (datetime.now() - self.heartbeat_at).total_seconds() > 60
