"""Bridge between workflow execution and entity state transitions.

Connects the workflow DAG executor to the transition engine so that
stage lifecycle events (start, complete, fail) automatically trigger
entity status transitions.

Supports two modes:
1. **Explicit**: Workflow YAML declares ``transitions`` per stage:
   ```yaml
   stages:
     - id: implement
       transitions:
         on_start: { status: in_progress }
         on_complete: { status: review }
         on_failure: { status: failed }
   ```
2. **Implicit**: Common stage names are mapped to well-known transitions
   (plan → planned, implement → in_progress, etc.).

The bridge emits ``ENTITY_STATUS_CHANGED`` events when transitions
succeed, allowing the dashboard and event stream to react.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixl.models.event import Event
    from pixl.state.engine import TransitionEngine, TransitionResult

logger = logging.getLogger(__name__)

# Implicit stage→status mapping

# Maps (stage_id or suffix) → { event_name → target_status }
# Used when a stage has no explicit ``transitions`` YAML config.
_IMPLICIT_MAP: dict[str, dict[str, str]] = {
    # Planning stages
    "plan": {"on_complete": "planned"},
    "tdd-plan": {"on_complete": "planned"},
    # Execution stages
    "implement": {"on_start": "in_progress", "on_complete": "review"},
    "execute": {"on_start": "in_progress", "on_complete": "review"},
    # Completion stages
    "complete": {"on_complete": "done"},
    "finish": {"on_complete": "done"},
    "finalize": {"on_complete": "done"},
    # Decomposition (epic workflows)
    "decompose": {"on_complete": "decomposed"},
    # Roadmap workflows
    "plan-milestones": {"on_complete": "planned"},
    "create-epics": {"on_complete": "in_progress"},
}

def _match_implicit(stage_id: str) -> dict[str, str]:
    """Find implicit transitions for a stage ID.

    Tries exact match first, then matches on the last segment
    (e.g., ``tdd-implement`` matches ``implement``).
    """
    if stage_id in _IMPLICIT_MAP:
        return _IMPLICIT_MAP[stage_id]

    # Try suffix match: "tdd-implement" → "implement"
    parts = stage_id.rsplit("-", 1)
    if len(parts) == 2 and parts[1] in _IMPLICIT_MAP:
        return _IMPLICIT_MAP[parts[1]]

    return {}

# TransitionSpec — parsed from YAML or implicit map

@dataclass(frozen=True)
class TransitionSpec:
    """A single transition specification for a stage event."""

    status: str
    note: str | None = None
    extra_context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict[str, Any] | str) -> TransitionSpec:
        """Parse from YAML config (dict or bare string)."""
        if isinstance(config, str):
            return cls(status=config)
        return cls(
            status=config["status"],
            note=config.get("note"),
            extra_context={k: v for k, v in config.items() if k not in ("status", "note")},
        )

# WorkflowStateBridge

class WorkflowStateBridge:
    """Bridges workflow stage events to entity state transitions.

    Usage::

        bridge = WorkflowStateBridge(engine)

        # After a stage completes:
        result = bridge.on_stage_complete("feat-001", "implement", stage_config)

        # Or with explicit context:
        result = bridge.on_stage_failed(
            "feat-001", "implement", stage_config,
            error="Test suite failed",
        )

    The bridge resolves the target status from:
    1. Explicit ``transitions`` block in the stage YAML config
    2. Implicit mapping based on the stage ID
    """

    def __init__(
        self,
        engine: TransitionEngine,
        event_callback: Callable[[Event], None] | None = None,
        session_id: str | None = None,
    ) -> None:
        self._engine = engine
        self._event_callback = event_callback
        self._session_id = session_id

    def set_event_callback(self, event_callback: Callable[[Event], None] | None) -> None:
        """Attach or replace the event callback for emitted events."""
        self._event_callback = event_callback

    def set_session_id(self, session_id: str | None) -> None:
        """Set the session ID used for emitted events."""
        self._session_id = session_id

    # Public API

    def on_stage_start(
        self,
        entity_id: str,
        stage_id: str,
        stage_config: dict[str, Any] | None = None,
        **context: Any,
    ) -> TransitionResult | None:
        """Called when a workflow stage begins execution."""
        return self._trigger("on_start", entity_id, stage_id, stage_config, **context)

    def on_stage_complete(
        self,
        entity_id: str,
        stage_id: str,
        stage_config: dict[str, Any] | None = None,
        **context: Any,
    ) -> TransitionResult | None:
        """Called when a workflow stage completes successfully."""
        return self._trigger("on_complete", entity_id, stage_id, stage_config, **context)

    def on_stage_failed(
        self,
        entity_id: str,
        stage_id: str,
        stage_config: dict[str, Any] | None = None,
        error: str | None = None,
        **context: Any,
    ) -> TransitionResult | None:
        """Called when a workflow stage fails."""
        if error:
            context["note"] = f"Stage '{stage_id}' failed: {error}"
        return self._trigger("on_failure", entity_id, stage_id, stage_config, **context)

    def resolve_target_status(
        self,
        event: str,
        stage_id: str,
        stage_config: dict[str, Any] | None = None,
    ) -> TransitionSpec | None:
        """Resolve what transition a stage event would trigger.

        Useful for dry-run / introspection without executing.
        """
        return self._resolve(event, stage_id, stage_config)

    # Internal

    def _trigger(
        self,
        event: str,
        entity_id: str,
        stage_id: str,
        stage_config: dict[str, Any] | None,
        **context: Any,
    ) -> TransitionResult | None:
        spec = self._resolve(event, stage_id, stage_config)
        if spec is None:
            return None

        session_id = context.pop("session_id", None)

        ctx: dict[str, Any] = {
            "trigger": "workflow",
            "trigger_id": stage_id,
        }
        ctx.update(spec.extra_context)
        ctx.update(context)
        if session_id is not None:
            ctx["session_id"] = session_id
        if spec.note:
            ctx.setdefault("note", spec.note)

        result = self._engine.transition(entity_id, spec.status, **ctx)

        if result.success:
            logger.info(
                "Stage '%s' %s → %s: %s → %s",
                stage_id,
                event,
                entity_id,
                result.from_status,
                result.to_status,
            )
            self._emit_status_event(entity_id, stage_id, result, session_id=session_id)
        elif result.error:
            logger.warning(
                "Stage '%s' %s → %s transition blocked: %s",
                stage_id,
                event,
                entity_id,
                result.error,
            )

        return result

    def _resolve(
        self,
        event: str,
        stage_id: str,
        stage_config: dict[str, Any] | None,
    ) -> TransitionSpec | None:
        """Resolve transition spec from explicit config or implicit map."""
        # 1. Explicit YAML config
        if stage_config:
            transitions = stage_config.get("transitions", {})
            event_config = transitions.get(event)
            if event_config:
                return TransitionSpec.from_config(event_config)

        # 2. Implicit mapping
        implicit = _match_implicit(stage_id)
        target = implicit.get(event)
        if target:
            return TransitionSpec(status=target)

        return None

    def _emit_status_event(
        self,
        entity_id: str,
        stage_id: str,
        result: TransitionResult,
        session_id: str | None = None,
    ) -> None:
        """Emit an ENTITY_STATUS_CHANGED event."""
        if self._event_callback is None:
            return

        from pixl.models.event import Event

        resolved_session_id = session_id or self._session_id or ""
        event = Event.entity_status_changed(
            session_id=resolved_session_id,
            entity_id=entity_id,
            from_status=result.from_status,
            to_status=result.to_status,
            stage_id=stage_id,
        )
        self._event_callback(event)
