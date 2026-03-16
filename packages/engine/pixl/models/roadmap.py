"""Roadmap model for tracking multi-epic strategic plans."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MilestoneStatus(StrEnum):
    """Lifecycle status of a milestone."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Milestone(BaseModel):
    """A milestone within a roadmap (e.g., v1.0, MVP, Beta).

    Milestones group phases/epics and define verification checkpoints.
    """

    id: str = Field(..., description="Milestone identifier (e.g., 'v1.0', 'mvp')")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    status: MilestoneStatus = Field(default=MilestoneStatus.PLANNED)

    # Linked entities
    epic_ids: list[str] = Field(default_factory=list)
    feature_ids: list[str] = Field(default_factory=list)

    # Success criteria for milestone audit
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Conditions that must hold for milestone completion",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Tracking
    notes: list[str] = Field(default_factory=list)

    def update_status(self, new_status: MilestoneStatus) -> None:
        """Update milestone status with timestamp."""
        self.status = new_status
        if new_status == MilestoneStatus.IN_PROGRESS and not self.started_at:
            self.started_at = datetime.now()
        elif new_status == MilestoneStatus.COMPLETED:
            self.completed_at = datetime.now()

    def add_note(self, note: str) -> None:
        """Add a timestamped note."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.append(f"[{timestamp}] {note}")

    @property
    def is_complete(self) -> bool:
        """Check if milestone is finished."""
        return self.status in (MilestoneStatus.COMPLETED, MilestoneStatus.FAILED)

    @property
    def entity_count(self) -> int:
        """Total linked entities (epics + features)."""
        return len(self.epic_ids) + len(self.feature_ids)


class RoadmapStatus(StrEnum):
    """Lifecycle status of a roadmap."""

    DRAFTING = "drafting"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Roadmap(BaseModel):
    """A roadmap representing a strategic plan spanning multiple epics."""

    id: str = Field(..., pattern=r"^roadmap-\d{3}$", description="Roadmap ID (e.g., roadmap-001)")
    title: str = Field(..., min_length=1, max_length=300)
    original_prompt: str = Field(default="")
    epic_ids: list[str] = Field(default_factory=list)
    milestones: list[dict[str, Any] | Milestone] = Field(default_factory=list)
    status: RoadmapStatus = Field(default=RoadmapStatus.DRAFTING)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    # Tracking
    notes: list[str] = Field(default_factory=list)

    def update_status(self, new_status: RoadmapStatus) -> None:
        """Update roadmap status with timestamp."""
        self.status = new_status
        self.updated_at = datetime.now()
        if new_status == RoadmapStatus.COMPLETED:
            self.completed_at = datetime.now()

    def add_epic(self, epic_id: str) -> None:
        """Add an epic to this roadmap."""
        if epic_id not in self.epic_ids:
            self.epic_ids.append(epic_id)
            self.updated_at = datetime.now()

    def add_milestone(self, milestone: Milestone) -> None:
        """Add a milestone to this roadmap."""
        self.milestones.append(milestone)
        self.updated_at = datetime.now()

    def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Get a milestone by ID."""
        for m in self.milestones:
            if isinstance(m, Milestone) and m.id == milestone_id:
                return m
            if isinstance(m, dict):
                raw_id = m.get("id") or m.get("name") or m.get("key")
                if raw_id == milestone_id:
                    # Best-effort conversion for dict milestones
                    title = m.get("title") or m.get("name") or str(raw_id)
                    status_val = m.get("status", "planned")
                    try:
                        status = MilestoneStatus(status_val)
                    except ValueError:
                        status = MilestoneStatus.PLANNED
                    return Milestone(
                        id=str(raw_id),
                        title=title,
                        description=m.get("description", ""),
                        status=status,
                        epic_ids=m.get("epic_ids", []),
                        feature_ids=m.get("feature_ids", []),
                        success_criteria=m.get("success_criteria", []),
                    )
        return None

    def add_note(self, note: str) -> None:
        """Add a timestamped note."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.now()

    @property
    def epic_count(self) -> int:
        """Number of epics in this roadmap."""
        return len(self.epic_ids)

    @property
    def milestone_count(self) -> int:
        """Number of milestones in this roadmap."""
        return len(self.milestones)
