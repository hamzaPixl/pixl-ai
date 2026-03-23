"""Transition side effects — actions executed after a status change.

Effects run after a transition has been validated and persisted.
They handle timestamp updates, status propagation, event emission,
and any other post-transition housekeeping.

Effects are guaranteed to run only after the transition succeeds.
They should be idempotent where possible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pixl.storage.db.backlog import BacklogDB


@dataclass(frozen=True)
class EffectResult:
    """Result of an effect execution."""

    effect_name: str
    applied: bool
    detail: str | None = None


class Effect(Protocol):
    """Protocol for transition side effects."""

    name: str

    def execute(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        store: BacklogDB,
        context: dict[str, Any],
    ) -> EffectResult: ...


# Built-in effects


class SetTimestamps:
    """Set lifecycle timestamps based on the new status.

    Features have: planned_at, started_at, completed_at
    Epics/Roadmaps have: completed_at only (no planned_at or started_at columns)

    Note: BacklogDB.update_feature_status() already handles this for
    features. This effect covers the case where the engine is used
    directly, and provides consistent behavior across entity types.
    """

    name = "set_timestamps"

    # Which timestamp columns exist per entity type
    _TIMESTAMP_MAP: dict[str, dict[str, str]] = {
        "feature": {
            "planned": "planned_at",
            "in_progress": "started_at",
            "done": "completed_at",
        },
        "epic": {
            "completed": "completed_at",
        },
        "roadmap": {
            "completed": "completed_at",
        },
    }

    def execute(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        store: BacklogDB,
        context: dict[str, Any],
    ) -> EffectResult:
        status_map = self._TIMESTAMP_MAP.get(entity_type, {})
        col = status_map.get(new_status)

        if not col:
            return EffectResult(self.name, applied=False, detail="no timestamp for this status")

        now = datetime.now().isoformat()
        updates = {col: now}

        if entity_type == "feature":
            store.update_feature(entity_id, **updates)
        elif entity_type == "epic":
            store.update_epic(entity_id, **updates)
        elif entity_type == "roadmap":
            store.update_roadmap(entity_id, **updates)

        return EffectResult(self.name, applied=True, detail=f"set {col}")


class RecordTransition:
    """Record the transition in the state_transitions audit table.

    Creates an immutable record of every status change for time-travel
    queries and analytics.
    """

    name = "record_transition"

    def execute(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        store: BacklogDB,
        context: dict[str, Any],
    ) -> EffectResult:
        trigger = context.get("trigger", "user")
        trigger_id = context.get("trigger_id")
        metadata = context.get("metadata")
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        session_id = context.get("session_id")
        if session_id is not None:
            metadata = {**metadata, "session_id": session_id}
        metadata_json = json.dumps(metadata) if metadata else None

        store._conn.execute(
            """INSERT INTO state_transitions
               (entity_type, entity_id, from_status, to_status, trigger, trigger_id, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entity_type, entity_id, old_status, new_status, trigger, trigger_id, metadata_json),
        )
        store._conn.commit()

        return EffectResult(
            self.name,
            applied=True,
            detail=f"{old_status} → {new_status} (trigger={trigger})",
        )


class AddTransitionNote:
    """Add a note recording the transition, if a note is provided in context."""

    name = "add_transition_note"

    def execute(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        store: BacklogDB,
        context: dict[str, Any],
    ) -> EffectResult:
        note = context.get("note")
        if not note:
            return EffectResult(self.name, applied=False, detail="no note provided")

        store.add_note(entity_type, entity_id, note)
        return EffectResult(self.name, applied=True, detail=note[:50])


class PropagateStatus:
    """Propagate feature status changes upward through the hierarchy.

    When a feature transitions, recalculates the parent epic's status.
    When an epic transitions, recalculates the parent roadmap's status.

    This uses the existing BacklogDB propagation logic.
    """

    name = "propagate_status"

    def execute(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        store: BacklogDB,
        context: dict[str, Any],
    ) -> EffectResult:
        if entity_type == "feature":
            store._propagate_status(entity_id)
            return EffectResult(self.name, applied=True, detail="feature → epic → roadmap")

        if entity_type == "epic":
            epic = store._conn.execute(
                "SELECT roadmap_id FROM epics WHERE id = ?", (entity_id,)
            ).fetchone()
            if epic and epic["roadmap_id"]:
                store._propagate_roadmap_status(epic["roadmap_id"])
                return EffectResult(
                    self.name, applied=True, detail=f"epic → roadmap {epic['roadmap_id']}"
                )

        return EffectResult(self.name, applied=False, detail="no parent to propagate to")


class ClearBlockedFields:
    """Clear blocked_by and blocked_reason when unblocking.

    Applies when transitioning FROM blocked to any other status.
    """

    name = "clear_blocked_fields"

    def execute(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        store: BacklogDB,
        context: dict[str, Any],
    ) -> EffectResult:
        if old_status != "blocked":
            return EffectResult(self.name, applied=False, detail="not unblocking")

        if entity_type == "feature":
            store.update_feature(entity_id, blocked_by=None, blocked_reason=None)
            return EffectResult(self.name, applied=True, detail="cleared blocked fields")

        return EffectResult(self.name, applied=False, detail="only applies to features")


class SetBlockedFields:
    """Set blocked_by and blocked_reason from context when blocking."""

    name = "set_blocked_fields"

    def execute(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        store: BacklogDB,
        context: dict[str, Any],
    ) -> EffectResult:
        if new_status != "blocked" or entity_type != "feature":
            return EffectResult(self.name, applied=False, detail="not blocking a feature")

        updates: dict[str, Any] = {}
        if context.get("blocked_by"):
            updates["blocked_by"] = context["blocked_by"]
        if context.get("blocked_reason"):
            updates["blocked_reason"] = context["blocked_reason"]

        if updates:
            store.update_feature(entity_id, **updates)
            return EffectResult(self.name, applied=True, detail=str(updates))

        return EffectResult(self.name, applied=False, detail="no blocking context provided")


# Default effect registry

# Effects are applied in order. Order matters:
# 1. Record the transition (audit trail)
# 2. Set timestamps
# 3. Handle blocking/unblocking fields
# 4. Add note
# 5. Propagate status (last, since it may trigger further transitions)
DEFAULT_EFFECTS: list[Effect] = [
    RecordTransition(),
    SetTimestamps(),
    SetBlockedFields(),
    ClearBlockedFields(),
    AddTransitionNote(),
    PropagateStatus(),
]
