"""Transition guards — preconditions checked before a status change.

Guards are functions that inspect the current entity state and return
whether a transition should proceed. They receive the entity dict
(from SQLite) and the BacklogDB store for querying related data.

Guards can be:
- HARD: Blocks the transition if failed. Used for invariants.
- SOFT: Emits a warning but allows the transition. Used for best practices.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pixl.storage.db.backlog import BacklogDB


class Severity(StrEnum):
    """Guard severity level."""

    HARD = "hard"  # Blocks the transition
    SOFT = "soft"  # Warning only, transition proceeds


@dataclass(frozen=True)
class GuardResult:
    """Result of a guard check."""

    passed: bool
    guard_name: str
    severity: Severity = Severity.HARD
    reason: str | None = None

    @staticmethod
    def ok(name: str) -> GuardResult:
        return GuardResult(passed=True, guard_name=name)

    @staticmethod
    def fail(name: str, reason: str, severity: Severity = Severity.HARD) -> GuardResult:
        return GuardResult(passed=False, guard_name=name, severity=severity, reason=reason)


class Guard(Protocol):
    """Protocol for transition guard functions."""

    name: str
    severity: Severity

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult: ...


# Feature guards


class DependenciesMet:
    """All dependencies must be done before starting work.

    Applies when transitioning to: in_progress
    """

    name = "dependencies_met"
    severity = Severity.HARD

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult:
        if to_status != "in_progress":
            return GuardResult.ok(self.name)

        feature_id = entity["id"]
        all_met, unmet_ids = store.check_dependencies_met(feature_id)

        if all_met:
            return GuardResult.ok(self.name)

        return GuardResult.fail(
            self.name,
            f"Unmet dependencies: {', '.join(unmet_ids)}",
        )


class HasPlan:
    """Feature should have a plan before starting execution.

    Soft guard — warns but doesn't block. Some workflows skip planning.
    Applies when transitioning to: in_progress
    """

    name = "has_plan"
    severity = Severity.SOFT

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult:
        if to_status != "in_progress":
            return GuardResult.ok(self.name)

        if entity.get("plan_path"):
            return GuardResult.ok(self.name)

        return GuardResult.fail(
            self.name,
            "No plan_path set. Consider running 'pixl plan' first.",
            severity=Severity.SOFT,
        )


class BlockReasonRequired:
    """A blocked_by or blocked_reason must be provided when blocking.

    Soft guard — encourages tracking why something is blocked.
    Applies when transitioning to: blocked
    """

    name = "block_reason_required"
    severity = Severity.SOFT

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult:
        if to_status != "blocked":
            return GuardResult.ok(self.name)

        if entity.get("blocked_by") or entity.get("blocked_reason"):
            return GuardResult.ok(self.name)

        return GuardResult.fail(
            self.name,
            "No blocked_by or blocked_reason provided.",
            severity=Severity.SOFT,
        )


# Epic guards


class EpicHasFeatures:
    """Epic must have at least one feature before decomposed/in_progress.

    Applies when transitioning to: decomposed, in_progress
    """

    name = "epic_has_features"
    severity = Severity.HARD

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult:
        if to_status not in ("decomposed", "in_progress"):
            return GuardResult.ok(self.name)

        feature_ids = entity.get("feature_ids", [])
        if feature_ids:
            return GuardResult.ok(self.name)

        return GuardResult.fail(
            self.name,
            "Epic has no features. Decompose it first.",
        )


class EpicAllFeaturesDone:
    """All features must be done before epic can be completed.

    Applies when transitioning to: completed
    """

    name = "epic_all_features_done"
    severity = Severity.HARD

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult:
        if to_status != "completed":
            return GuardResult.ok(self.name)

        feature_ids = entity.get("feature_ids", [])
        if not feature_ids:
            return GuardResult.ok(self.name)

        progress = entity.get("progress", {})
        total = progress.get("total", 0)
        done = progress.get("done", 0)

        if total > 0 and done < total:
            pending = total - done
            return GuardResult.fail(
                self.name,
                f"{pending} of {total} features not done yet.",
            )

        return GuardResult.ok(self.name)


# Roadmap guards


class RoadmapHasEpics:
    """Roadmap must have at least one epic before planned/in_progress.

    Applies when transitioning to: planned, in_progress
    """

    name = "roadmap_has_epics"
    severity = Severity.HARD

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult:
        if to_status not in ("planned", "in_progress"):
            return GuardResult.ok(self.name)

        epic_ids = entity.get("epic_ids", [])
        if epic_ids:
            return GuardResult.ok(self.name)

        return GuardResult.fail(
            self.name,
            "Roadmap has no epics.",
        )


class RoadmapAllEpicsDone:
    """All epics must be completed before roadmap can be completed.

    Applies when transitioning to: completed
    """

    name = "roadmap_all_epics_done"
    severity = Severity.HARD

    def check(
        self,
        entity: dict[str, Any],
        to_status: str,
        store: BacklogDB,
    ) -> GuardResult:
        if to_status != "completed":
            return GuardResult.ok(self.name)

        epic_ids = entity.get("epic_ids", [])
        if not epic_ids:
            return GuardResult.ok(self.name)

        not_done = []
        for eid in epic_ids:
            epic = store.get_epic(eid)
            if epic and epic.get("status") != "completed":
                not_done.append(eid)

        if not_done:
            return GuardResult.fail(
                self.name,
                f"Epics not completed: {', '.join(not_done)}",
            )

        return GuardResult.ok(self.name)


# Default guard registry

# Maps (entity_type) → list of Guard instances
DEFAULT_GUARDS: dict[str, list[Guard]] = {
    "feature": [
        DependenciesMet(),
        HasPlan(),
        BlockReasonRequired(),
    ],
    "epic": [
        EpicHasFeatures(),
        EpicAllFeaturesDone(),
    ],
    "roadmap": [
        RoadmapHasEpics(),
        RoadmapAllEpicsDone(),
    ],
}
