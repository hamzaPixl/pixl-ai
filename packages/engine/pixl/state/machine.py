"""State machine definitions for entity lifecycle management.

Defines the allowed transitions for each entity type (Feature, Epic, Roadmap)
as a directed graph. The state machine is the first check in the transition
pipeline — if a transition isn't in the graph, it's rejected immediately.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Transition:
    """A single allowed state transition."""

    from_status: str
    to_status: str

    def __repr__(self) -> str:
        return f"{self.from_status} → {self.to_status}"


@dataclass
class StateMachine:
    """State machine for a single entity type.

    Defines which status transitions are allowed. Any transition not
    explicitly listed is rejected.
    """

    entity_type: str
    transitions: set[Transition] = field(default_factory=set)

    def is_allowed(self, from_status: str, to_status: str) -> bool:
        """Check if a transition is allowed."""
        return Transition(from_status, to_status) in self.transitions

    def get_reachable(self, from_status: str) -> set[str]:
        """Get all statuses reachable from the given status."""
        return {t.to_status for t in self.transitions if t.from_status == from_status}

    def get_all_statuses(self) -> set[str]:
        """Get all statuses in the machine."""
        statuses: set[str] = set()
        for t in self.transitions:
            statuses.add(t.from_status)
            statuses.add(t.to_status)
        return statuses


# Feature state machine
#
#   backlog ──→ planned ──→ in_progress ──→ review ──→ done
#     ↑  ↕          │↕           │              │
#     │  deferred ←─┘            ↓              ↓
#     ←──────── blocked ←───────┘           failed
#     ↑                                       │
#     └───────────────────────────────────────┘
#
FEATURE_MACHINE = StateMachine(
    entity_type="feature",
    transitions={
        # Happy path
        Transition("backlog", "planned"),
        Transition("planned", "in_progress"),
        Transition("in_progress", "review"),
        Transition("review", "done"),
        # Skip plan (direct exec)
        Transition("backlog", "in_progress"),
        # Back to work from review
        Transition("review", "in_progress"),
        # Blocking (from any active state)
        Transition("backlog", "blocked"),
        Transition("planned", "blocked"),
        Transition("in_progress", "blocked"),
        # Unblocking (back to actionable)
        Transition("blocked", "backlog"),
        Transition("blocked", "planned"),
        Transition("blocked", "in_progress"),
        # Failure (from any active state)
        Transition("backlog", "failed"),
        Transition("planned", "failed"),
        Transition("in_progress", "failed"),
        Transition("review", "failed"),
        Transition("blocked", "failed"),
        Transition("failed", "backlog"),
        # Rework from done (rare but valid)
        Transition("done", "in_progress"),
        # Deferral (from pre-execution states)
        Transition("backlog", "deferred"),
        Transition("planned", "deferred"),
        Transition("blocked", "deferred"),
        # Reactivation (from deferred)
        Transition("deferred", "backlog"),
        Transition("deferred", "planned"),
    },
)

# Epic state machine
#
#   drafting ──→ decomposed ──→ in_progress ──→ completed
#     ↑              │              │
#     │              ↓              ↓
#     └────────── failed ←─────────┘
#
EPIC_MACHINE = StateMachine(
    entity_type="epic",
    transitions={
        # Happy path
        Transition("drafting", "decomposed"),
        Transition("decomposed", "in_progress"),
        Transition("in_progress", "completed"),
        # Skip decompose (auto-promoted by propagation)
        Transition("drafting", "in_progress"),
        # Failure
        Transition("drafting", "failed"),
        Transition("decomposed", "failed"),
        Transition("in_progress", "failed"),
        Transition("failed", "drafting"),
    },
)

# Roadmap state machine
#
#   drafting ──→ planned ──→ in_progress ──→ completed
#     ↑            │              │
#     │            ↓              ↓
#     └────────── failed ←───────┘
#
ROADMAP_MACHINE = StateMachine(
    entity_type="roadmap",
    transitions={
        # Happy path
        Transition("drafting", "planned"),
        Transition("planned", "in_progress"),
        Transition("in_progress", "completed"),
        # Skip plan (auto-promoted by propagation)
        Transition("drafting", "in_progress"),
        # Direct completion (small roadmaps)
        Transition("planned", "completed"),
        # Failure (from any active state)
        Transition("drafting", "failed"),
        Transition("planned", "failed"),
        Transition("in_progress", "failed"),
        Transition("failed", "drafting"),
    },
)

# Registry mapping entity type prefix to machine
MACHINES: dict[str, StateMachine] = {
    "feature": FEATURE_MACHINE,
    "epic": EPIC_MACHINE,
    "roadmap": ROADMAP_MACHINE,
}


def get_machine(entity_id: str) -> StateMachine:
    """Look up the state machine for an entity by its ID prefix.

    Args:
        entity_id: Entity ID (e.g., "feat-001", "epic-002", "roadmap-001")

    Returns:
        The matching StateMachine.

    Raises:
        ValueError: If entity type cannot be determined.
    """
    prefix = entity_id.split("-")[0]
    mapping = {"feat": "feature", "epic": "epic", "roadmap": "roadmap"}
    entity_type = mapping.get(prefix)
    if entity_type is None:
        raise ValueError(f"Unknown entity prefix: {prefix!r} (from {entity_id!r})")
    return MACHINES[entity_type]
