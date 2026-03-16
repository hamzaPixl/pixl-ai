"""Epic model for tracking multi-feature work items."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EpicStatus(StrEnum):
    """Lifecycle status of an epic."""

    DRAFTING = "drafting"
    DECOMPOSED = "decomposed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Epic(BaseModel):
    """An epic representing a multi-feature body of work."""

    id: str = Field(..., pattern=r"^epic-\d{3}$", description="Epic ID (e.g., epic-001)")
    title: str = Field(..., min_length=1, max_length=300)
    original_prompt: str = Field(default="")
    feature_ids: list[str] = Field(default_factory=list)
    workflow_id: str | None = None
    status: EpicStatus = Field(default=EpicStatus.DRAFTING)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    # Tracking
    notes: list[str] = Field(default_factory=list)

    def update_status(self, new_status: EpicStatus) -> None:
        """Update epic status with timestamp."""
        self.status = new_status
        self.updated_at = datetime.now()
        if new_status == EpicStatus.COMPLETED:
            self.completed_at = datetime.now()

    def add_feature(self, feature_id: str) -> None:
        """Add a feature to this epic."""
        if feature_id not in self.feature_ids:
            self.feature_ids.append(feature_id)
            self.updated_at = datetime.now()

    def add_note(self, note: str) -> None:
        """Add a timestamped note."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.now()

    @property
    def feature_count(self) -> int:
        """Number of features in this epic."""
        return len(self.feature_ids)
