"""Feature model for tracking work items."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FeatureType(StrEnum):
    """Type of work item."""

    FEATURE = "feature"
    BUG = "bug"
    REFACTOR = "refactor"
    DOCS = "docs"
    CHORE = "chore"
    EXECUTION = "execution"


class Priority(StrEnum):
    """Priority level for features."""

    P0 = "P0"  # Critical - drop everything
    P1 = "P1"  # High - do soon
    P2 = "P2"  # Medium - normal priority
    P3 = "P3"  # Low - when time permits


class FeatureStatus(StrEnum):
    """Lifecycle status of a feature."""

    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    DONE = "done"
    FAILED = "failed"


class Feature(BaseModel):
    """A feature or work item to be implemented."""

    id: str = Field(..., pattern=r"^feat-\d{3}$", description="Feature ID (e.g., feat-001)")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    type: FeatureType = Field(default=FeatureType.FEATURE)
    priority: Priority = Field(default=Priority.P2)
    status: FeatureStatus = Field(default=FeatureStatus.BACKLOG)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None
    planned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Parent references
    epic_id: str | None = Field(default=None, description="Parent epic ID (e.g., epic-001)")
    roadmap_id: str | None = Field(
        default=None, description="Parent roadmap ID (e.g., roadmap-001)"
    )

    # Dependencies
    depends_on: list[str] = Field(default_factory=list)
    blocked_by: str | None = None
    blocked_reason: str | None = None

    # Tracking
    plan_path: str | None = None
    pr_url: str | None = None
    branch_name: str | None = None

    # Metrics
    estimated_hours: float | None = None
    actual_hours: float | None = None
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    # Verification
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Explicit success criteria derived from plan (for goal-backward verification)",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Implicit assumptions surfaced during planning (for pre-execution validation)",
    )

    # Notes
    notes: list[str] = Field(default_factory=list)

    def update_status(self, new_status: FeatureStatus) -> None:
        """Update feature status and set appropriate timestamps."""
        self.status = new_status
        self.updated_at = datetime.now()

        if new_status == FeatureStatus.PLANNED:
            self.planned_at = datetime.now()
        elif new_status == FeatureStatus.IN_PROGRESS:
            self.started_at = datetime.now()
        elif new_status == FeatureStatus.DONE:
            self.completed_at = datetime.now()

    def add_note(self, note: str) -> None:
        """Add a timestamped note."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.now()

    def add_cost(self, cost_usd: float, tokens: int) -> None:
        """Track cost and token usage."""
        self.total_cost_usd += cost_usd
        self.total_tokens += tokens
        self.updated_at = datetime.now()

    @property
    def is_actionable(self) -> bool:
        """Check if feature can be worked on."""
        return self.status in (FeatureStatus.BACKLOG, FeatureStatus.PLANNED)

    @property
    def is_complete(self) -> bool:
        """Check if feature is finished."""
        return self.status in (FeatureStatus.DONE, FeatureStatus.FAILED)

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = [
            f"# {self.id}: {self.title}",
            "",
            f"**Type:** {self.type.value}",
            f"**Priority:** {self.priority.value}",
            f"**Status:** {self.status.value}",
            "",
            "## Description",
            self.description or "_No description_",
            "",
        ]

        if self.depends_on:
            lines.extend(["## Dependencies", ""])
            for dep in self.depends_on:
                lines.append(f"- {dep}")
            lines.append("")

        if self.notes:
            lines.extend(["## Notes", ""])
            for note in self.notes:
                lines.append(f"- {note}")
            lines.append("")

        if self.total_cost_usd > 0:
            lines.extend(
                [
                    "## Metrics",
                    f"- **Cost:** ${self.total_cost_usd:.4f}",
                    f"- **Tokens:** {self.total_tokens:,}",
                    "",
                ]
            )

        return "\n".join(lines)
