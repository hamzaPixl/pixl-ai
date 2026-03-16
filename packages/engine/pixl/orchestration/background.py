"""Background task management for parallel agent execution."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    """Status of a background task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class BackgroundTask(BaseModel):
    """A background task running an agent."""

    id: str
    agent: str
    prompt: str
    model: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: list[dict[str, Any]] = Field(default_factory=list)
    result: str | None = None
    error: str | None = None

    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()

    def complete(self, result: str) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.ERROR
        self.completed_at = datetime.now()
        self.error = error

    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()

    def append_output(self, chunk: dict[str, Any]) -> None:
        """Append an output chunk."""
        self.output.append(chunk)

    @property
    def is_finished(self) -> bool:
        """Check if task is finished (completed, error, or cancelled)."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.ERROR,
            TaskStatus.CANCELLED,
        )
