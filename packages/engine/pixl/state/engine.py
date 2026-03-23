"""Transition engine — orchestrates state machine, guards, and effects.

The engine is the single entry point for all status changes. It:
1. Validates the transition against the state machine
2. Runs guards (precondition checks)
3. Persists the status change
4. Runs effects (post-transition side effects)

Usage:
    from pixl.state import TransitionEngine

    engine = TransitionEngine.default(backlog_db)

    can, reasons = engine.can_transition("feat-001", "in_progress")

    result = engine.transition("feat-001", "in_progress", trigger="user")

    # With blocking context
    result = engine.transition("feat-001", "blocked",
        blocked_by="feat-002",
        blocked_reason="Waiting on API",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pixl.state.effects import DEFAULT_EFFECTS, Effect, EffectResult
from pixl.state.guards import DEFAULT_GUARDS, Guard, GuardResult, Severity
from pixl.state.machine import MACHINES, StateMachine


@dataclass(frozen=True)
class TransitionResult:
    """Result of a transition attempt."""

    success: bool
    entity_id: str
    from_status: str
    to_status: str
    guard_results: list[GuardResult] = field(default_factory=list)
    effect_results: list[EffectResult] = field(default_factory=list)
    error: str | None = None

    @property
    def warnings(self) -> list[GuardResult]:
        """Get soft guard failures (warnings)."""
        return [g for g in self.guard_results if not g.passed and g.severity == Severity.SOFT]

    @property
    def hard_failures(self) -> list[GuardResult]:
        """Get hard guard failures (blockers)."""
        return [g for g in self.guard_results if not g.passed and g.severity == Severity.HARD]


class TransitionEngine:
    """Orchestrates state transitions with validation, guards, and effects.

    The engine wraps BacklogDB and provides a safe, validated interface
    for all status changes. Direct BacklogDB.update_*_status() calls
    bypass the engine and should be avoided in new code.
    """

    def __init__(
        self,
        store: Any,  # BacklogDB
        machines: dict[str, StateMachine] | None = None,
        guards: dict[str, list[Guard]] | None = None,
        effects: list[Effect] | None = None,
    ) -> None:
        self._store = store
        self._machines = machines if machines is not None else dict(MACHINES)
        self._guards = (
            guards if guards is not None else {k: list(v) for k, v in DEFAULT_GUARDS.items()}
        )
        self._effects = effects if effects is not None else list(DEFAULT_EFFECTS)

    @classmethod
    def default(cls, store: Any) -> TransitionEngine:
        """Create an engine with all default machines, guards, and effects."""
        return cls(store)

    # Public API

    def transition(
        self,
        entity_id: str,
        to_status: str,
        **context: Any,
    ) -> TransitionResult:
        """Execute a status transition.

        Args:
            entity_id: Entity ID (e.g., "feat-001", "epic-002")
            to_status: Target status string
            **context: Additional context passed to guards and effects.
                Common keys:
                - trigger: What triggered the transition ("user", "auto_propagation", etc.)
                - trigger_id: ID of the triggering entity
                - note: Note to attach to the transition
                - blocked_by: Feature ID blocking this one
                - blocked_reason: Reason for blocking

        Returns:
            TransitionResult with success/failure info.
        """
        entity_type = self._resolve_entity_type(entity_id)
        if entity_type is None:
            return TransitionResult(
                success=False,
                entity_id=entity_id,
                from_status="",
                to_status=to_status,
                error=f"Unknown entity type for {entity_id!r}",
            )

        entity = self._get_entity(entity_type, entity_id)
        if entity is None:
            return TransitionResult(
                success=False,
                entity_id=entity_id,
                from_status="",
                to_status=to_status,
                error=f"Entity {entity_id!r} not found",
            )

        from_status = entity["status"]

        # Same status — no-op
        if from_status == to_status:
            return TransitionResult(
                success=True,
                entity_id=entity_id,
                from_status=from_status,
                to_status=to_status,
            )

        machine = self._machines.get(entity_type)
        if machine and not machine.is_allowed(from_status, to_status):
            return TransitionResult(
                success=False,
                entity_id=entity_id,
                from_status=from_status,
                to_status=to_status,
                error=f"Transition {from_status} → {to_status} not allowed for {entity_type}",
            )

        guard_results = self._run_guards(entity_type, entity, to_status)
        hard_failures = [g for g in guard_results if not g.passed and g.severity == Severity.HARD]

        if hard_failures:
            return TransitionResult(
                success=False,
                entity_id=entity_id,
                from_status=from_status,
                to_status=to_status,
                guard_results=guard_results,
                error=f"Guard failed: {hard_failures[0].reason}",
            )

        self._persist_status(entity_type, entity_id, to_status)

        effect_results = self._run_effects(entity_type, entity_id, from_status, to_status, context)

        return TransitionResult(
            success=True,
            entity_id=entity_id,
            from_status=from_status,
            to_status=to_status,
            guard_results=guard_results,
            effect_results=effect_results,
        )

    def can_transition(
        self,
        entity_id: str,
        to_status: str,
    ) -> tuple[bool, list[str]]:
        """Check if a transition is possible without executing it.

        Returns:
            (can_transition, list_of_reasons_if_not)
        """
        entity_type = self._resolve_entity_type(entity_id)
        if entity_type is None:
            return False, [f"Unknown entity type for {entity_id!r}"]

        entity = self._get_entity(entity_type, entity_id)
        if entity is None:
            return False, [f"Entity {entity_id!r} not found"]

        from_status = entity["status"]
        if from_status == to_status:
            return True, []

        # Check state machine
        machine = self._machines.get(entity_type)
        if machine and not machine.is_allowed(from_status, to_status):
            return False, [f"Transition {from_status} → {to_status} not allowed"]

        # Check hard guards only
        guard_results = self._run_guards(entity_type, entity, to_status)
        hard_failures = [g for g in guard_results if not g.passed and g.severity == Severity.HARD]

        if hard_failures:
            return False, [g.reason or g.guard_name for g in hard_failures]

        return True, []

    def get_available_transitions(self, entity_id: str) -> list[str]:
        """Get all statuses this entity can transition to right now.

        Checks both the state machine and hard guards.
        """
        entity_type = self._resolve_entity_type(entity_id)
        if entity_type is None:
            return []

        entity = self._get_entity(entity_type, entity_id)
        if entity is None:
            return []

        machine = self._machines.get(entity_type)
        if machine is None:
            return []

        from_status = entity["status"]
        reachable = machine.get_reachable(from_status)

        available = []
        for target in sorted(reachable):
            can, _ = self.can_transition(entity_id, target)
            if can:
                available.append(target)

        return available

    # Guard / Effect registration

    def register_guard(self, entity_type: str, guard: Guard) -> None:
        """Register a custom guard for an entity type."""
        self._guards.setdefault(entity_type, []).append(guard)

    def register_effect(self, effect: Effect) -> None:
        """Register a custom effect (runs for all entity types)."""
        self._effects.append(effect)

    # Internal helpers

    def _resolve_entity_type(self, entity_id: str) -> str | None:
        """Resolve entity type from ID prefix."""
        prefix = entity_id.split("-")[0]
        return {"feat": "feature", "epic": "epic", "roadmap": "roadmap"}.get(prefix)

    def _get_entity(self, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        """Fetch entity from the store."""
        result: dict[str, Any] | None = None
        if entity_type == "feature":
            result = self._store.get_feature(entity_id)
        elif entity_type == "epic":
            result = self._store.get_epic(entity_id)
        elif entity_type == "roadmap":
            result = self._store.get_roadmap(entity_id)
        return result

    def _persist_status(self, entity_type: str, entity_id: str, new_status: str) -> None:
        """Persist the status change to SQLite.

        Uses raw UPDATE (not update_*_status) to avoid duplicate
        transition recording — the engine handles that via effects.
        """
        import sqlite3
        import time
        from datetime import datetime

        now = datetime.now().isoformat()
        table = {"feature": "features", "epic": "epics", "roadmap": "roadmaps"}[entity_type]

        for attempt in range(5):
            try:
                self._store._conn.execute(
                    f"UPDATE {table} SET status = ?, updated_at = ? WHERE id = ?",
                    (new_status, now, entity_id),
                )
                self._store._conn.commit()
                return
            except sqlite3.OperationalError as exc:
                if "database is locked" in str(exc).lower() and attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise

    def _run_guards(
        self,
        entity_type: str,
        entity: dict[str, Any],
        to_status: str,
    ) -> list[GuardResult]:
        """Run all guards for this entity type."""
        guards = self._guards.get(entity_type, [])
        results = []
        for guard in guards:
            result = guard.check(entity, to_status, self._store)
            results.append(result)
        return results

    def _run_effects(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        context: dict[str, Any],
    ) -> list[EffectResult]:
        """Run all effects after a successful transition."""
        results = []
        for effect in self._effects:
            result = effect.execute(
                entity_type, entity_id, old_status, new_status, self._store, context
            )
            results.append(result)
        return results
