"""State management — transition engine, state machines, guards, and effects.

The state module provides a validated, audited pipeline for all entity
status changes in the Roadmap → Epic → Feature hierarchy.

Usage:
    from pixl.state import TransitionEngine

    engine = TransitionEngine.default(backlog_db)
    result = engine.transition("feat-001", "in_progress", trigger="user")

    if result.success:
        print(f"Transitioned: {result.from_status} → {result.to_status}")
    else:
        print(f"Blocked: {result.error}")

    # Check what's possible
    available = engine.get_available_transitions("feat-001")
"""

from pixl.state.effects import Effect, EffectResult
from pixl.state.engine import TransitionEngine, TransitionResult
from pixl.state.guards import Guard, GuardResult, Severity
from pixl.state.machine import (
    EPIC_MACHINE,
    FEATURE_MACHINE,
    ROADMAP_MACHINE,
    StateMachine,
    Transition,
    get_machine,
)
from pixl.state.workflow_bridge import TransitionSpec, WorkflowStateBridge

__all__ = [
    "TransitionEngine",
    "TransitionResult",
    "Guard",
    "GuardResult",
    "Severity",
    "Effect",
    "EffectResult",
    "StateMachine",
    "Transition",
    "FEATURE_MACHINE",
    "EPIC_MACHINE",
    "ROADMAP_MACHINE",
    "get_machine",
    "WorkflowStateBridge",
    "TransitionSpec",
]
