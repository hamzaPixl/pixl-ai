"""Boulder state model for tracking plan execution.

Named after Sisyphus's boulder - the eternal task that must be rolled.
Tracks active plan, progress through checkboxes, and session history.
"""

import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

class PlanProgress(BaseModel):
    """Progress through a plan's checkboxes."""

    total: int = Field(default=0, description="Total number of checkboxes")
    completed: int = Field(default=0, description="Number of completed checkboxes")

    @property
    def is_complete(self) -> bool:
        """Check if all tasks are done."""
        return self.total > 0 and self.completed >= self.total

    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    def __str__(self) -> str:
        """Human-readable progress string."""
        return f"{self.completed}/{self.total} ({self.percentage:.0f}%)"

class BoulderState(BaseModel):
    """Manages the active work plan state for orchestration.

    Tracks which plan is being executed, progress through the plan,
    and which sessions have worked on it.
    """

    active_plan: str | None = Field(
        default=None,
        description="Absolute path to the active plan file",
    )
    plan_name: str | None = Field(
        default=None,
        description="Plan name derived from filename",
    )
    feature_id: str | None = Field(
        default=None,
        description="Feature ID this plan belongs to",
    )
    started_at: datetime | None = Field(
        default=None,
        description="ISO timestamp when work started",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="ISO timestamp of last update",
    )
    session_ids: list[str] = Field(
        default_factory=list,
        description="Session IDs that have worked on this plan",
    )
    progress: PlanProgress = Field(
        default_factory=PlanProgress,
        description="Checkbox progress through the plan",
    )

    @property
    def is_active(self) -> bool:
        """Check if there's an active plan."""
        return self.active_plan is not None

    @property
    def is_complete(self) -> bool:
        """Check if the plan is complete."""
        return self.progress.is_complete

    def start_plan(
        self,
        plan_path: str | Path,
        feature_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Start tracking a new plan.

        Args:
            plan_path: Path to the plan file
            feature_id: Optional feature ID
            session_id: Optional initial session ID
        """
        path = Path(plan_path)
        self.active_plan = str(path.resolve())
        self.plan_name = path.stem
        self.feature_id = feature_id
        self.started_at = datetime.now()
        self.updated_at = datetime.now()
        self.session_ids = [session_id] if session_id else []
        self.progress = PlanProgress()

        if path.exists():
            self.update_progress_from_file()

    def add_session(self, session_id: str) -> None:
        """Add a session ID that's working on this plan.

        Args:
            session_id: Session ID to add
        """
        if session_id and session_id not in self.session_ids:
            self.session_ids.append(session_id)
            self.updated_at = datetime.now()

    def update_progress_from_file(self) -> PlanProgress:
        """Parse the plan file and update checkbox progress.

        Returns:
            Updated PlanProgress
        """
        if not self.active_plan:
            return self.progress

        path = Path(self.active_plan)
        if not path.exists():
            return self.progress

        content = path.read_text(encoding="utf-8")
        self.progress = self.parse_checkbox_progress(content)
        self.updated_at = datetime.now()
        return self.progress

    @staticmethod
    def parse_checkbox_progress(content: str) -> PlanProgress:
        """Parse markdown content for checkbox progress.

        Looks for:
        - [ ] unchecked
        - [x] or [X] checked

        Args:
            content: Markdown content to parse

        Returns:
            PlanProgress with counts
        """
        # Match markdown checkboxes: - [ ] or - [x] or - [X]
        # Also matches * [ ] style
        checkbox_pattern = r"^[\s]*[-*]\s*\[([ xX])\]"

        total = 0
        completed = 0

        for line in content.split("\n"):
            match = re.match(checkbox_pattern, line)
            if match:
                total += 1
                if match.group(1).lower() == "x":
                    completed += 1

        return PlanProgress(total=total, completed=completed)

    def clear(self) -> None:
        """Clear the boulder state (plan completed or abandoned)."""
        self.active_plan = None
        self.plan_name = None
        self.feature_id = None
        self.started_at = None
        self.updated_at = datetime.now()
        self.session_ids = []
        self.progress = PlanProgress()

    def to_summary(self) -> str:
        """Generate a summary string for display.

        Returns:
            Human-readable summary of boulder state
        """
        if not self.is_active:
            return "No active plan"

        lines = [
            f"Plan: {self.plan_name}",
            f"Progress: {self.progress}",
        ]

        if self.feature_id:
            lines.insert(0, f"Feature: {self.feature_id}")

        if self.started_at:
            elapsed = datetime.now() - self.started_at
            hours = elapsed.total_seconds() / 3600
            lines.append(f"Duration: {hours:.1f}h")

        if self.session_ids:
            lines.append(f"Sessions: {len(self.session_ids)}")

        return " | ".join(lines)
