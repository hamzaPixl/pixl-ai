"""Storage for boulder state (active plan tracking)."""

import json
from pathlib import Path

from pixl.models.boulder import BoulderState, PlanProgress
from pixl.paths import get_pixl_dir


class BoulderStore:
    """Manages persistence of boulder state.

    Stores the active plan state in .pixl/boulder.json
    """

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.pixl_dir = get_pixl_dir(project_path)
        self.boulder_path = self.pixl_dir / "boulder.json"

    def _ensure_dir(self) -> None:
        """Ensure .pixl directory exists."""
        self.pixl_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> BoulderState:
        """Load boulder state from disk, or create empty one."""
        if not self.boulder_path.exists():
            return BoulderState()

        with open(self.boulder_path, encoding="utf-8") as f:
            data = json.load(f)

        return BoulderState.model_validate(data)

    def save(self, state: BoulderState) -> None:
        """Save boulder state to disk."""
        self._ensure_dir()

        with open(self.boulder_path, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, indent=2, default=str)

    def start_plan(
        self,
        plan_path: str | Path,
        feature_id: str | None = None,
        session_id: str | None = None,
    ) -> BoulderState:
        """Start tracking a new plan.

        Args:
            plan_path: Path to the plan file
            feature_id: Optional feature ID
            session_id: Optional initial session ID

        Returns:
            Updated BoulderState
        """
        state = BoulderState()
        state.start_plan(plan_path, feature_id, session_id)
        self.save(state)
        return state

    def add_session(self, session_id: str) -> BoulderState:
        """Add a session ID to the active plan.

        Args:
            session_id: Session ID to add

        Returns:
            Updated BoulderState
        """
        state = self.load()
        if state.is_active:
            state.add_session(session_id)
            self.save(state)
        return state

    def update_progress(self) -> PlanProgress:
        """Re-parse the plan file and update progress.

        Returns:
            Updated PlanProgress
        """
        state = self.load()
        if state.is_active:
            progress = state.update_progress_from_file()
            self.save(state)
            return progress
        return PlanProgress()

    def get_progress(self) -> PlanProgress:
        """Get current progress without re-parsing file.

        Returns:
            Current PlanProgress
        """
        return self.load().progress

    def is_active(self) -> bool:
        """Check if there's an active plan.

        Returns:
            True if a plan is being tracked
        """
        return self.load().is_active

    def is_complete(self) -> bool:
        """Check if the active plan is complete.

        Returns:
            True if all checkboxes are done
        """
        state = self.load()
        if state.is_active:
            state.update_progress_from_file()
            self.save(state)
            return state.is_complete
        return False

    def get_active_plan(self) -> str | None:
        """Get the path to the active plan file.

        Returns:
            Plan file path or None
        """
        return self.load().active_plan

    def get_feature_id(self) -> str | None:
        """Get the feature ID for the active plan.

        Returns:
            Feature ID or None
        """
        return self.load().feature_id

    def clear(self) -> None:
        """Clear the boulder state (plan completed or abandoned)."""
        state = self.load()
        state.clear()
        self.save(state)

    def complete_plan(self) -> BoulderState:
        """Mark the current plan as complete and clear state.

        Returns:
            Final BoulderState before clearing
        """
        state = self.load()
        final_state = state.model_copy()
        state.clear()
        self.save(state)
        return final_state

    def exists(self) -> bool:
        """Check if boulder state file exists."""
        return self.boulder_path.exists()

    def get_summary(self) -> str:
        """Get a human-readable summary of current state.

        Returns:
            Summary string
        """
        return self.load().to_summary()
