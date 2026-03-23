"""Node instance models for runtime state.

This module defines the runtime state of nodes during workflow execution.
The key distinction is:
- Node (in workflow.py) = immutable definition (stored once, referenced by hash)
- NodeInstance (here) = mutable runtime state (stored in SQLite session)

This separation keeps the session data small and guarantees the snapshot is
the only source of structural truth.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any


class NodeState(StrEnum):
    """Runtime state for ANY node type.

    This is the single source of truth for node state.
    No separate TaskState/GateState enums needed—this IS the runtime state.
    """

    # Task node states
    TASK_PENDING = "task_pending"
    TASK_RUNNING = "task_running"
    TASK_PAUSED = "task_paused"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_BLOCKED = "task_blocked"
    TASK_SKIPPED = "task_skipped"

    # Gate node states
    GATE_PENDING = "gate_pending"
    GATE_WAITING = "gate_waiting"
    GATE_APPROVED = "gate_approved"
    GATE_REJECTED = "gate_rejected"
    GATE_TIMEOUT = "gate_timeout"

    # Parallel/Merge node states
    PARALLEL_WAITING = "parallel_waiting"
    PARALLEL_READY = "parallel_ready"
    MERGE_WAITING = "merge_waiting"

    @classmethod
    def is_terminal(cls, state: "NodeState") -> bool:
        """Check if a state is terminal (no further transitions)."""
        terminal = {
            cls.TASK_COMPLETED,
            cls.TASK_FAILED,
            cls.TASK_SKIPPED,
            cls.GATE_APPROVED,
            cls.GATE_REJECTED,
            cls.GATE_TIMEOUT,
        }
        return state in terminal

    @classmethod
    def is_active(cls, state: "NodeState") -> bool:
        """Check if a state is active (currently executing)."""
        active = {
            cls.TASK_RUNNING,
            cls.GATE_WAITING,
        }
        return state in active

    @classmethod
    def can_transition_to(cls, from_state: "NodeState", to_state: "NodeState") -> bool:
        """Check if a state transition is valid."""
        # Pending can go to running, blocked, or skipped
        if from_state == cls.TASK_PENDING:
            return to_state in {
                cls.TASK_RUNNING,
                cls.TASK_BLOCKED,
                cls.TASK_SKIPPED,
            }
        if from_state == cls.GATE_PENDING:
            return to_state in {cls.GATE_WAITING, cls.TASK_SKIPPED}

        # Running can go to completed, failed, or paused
        if from_state == cls.TASK_RUNNING:
            return to_state in {
                cls.TASK_COMPLETED,
                cls.TASK_FAILED,
                cls.TASK_PAUSED,
            }

        # Waiting can go to approved, rejected, or timeout
        if from_state == cls.GATE_WAITING:
            return to_state in {
                cls.GATE_APPROVED,
                cls.GATE_REJECTED,
                cls.GATE_TIMEOUT,
            }

        # Paused can go back to running
        if from_state == cls.TASK_PAUSED:
            return to_state == cls.TASK_RUNNING

        # Blocked can go to pending (unblocked) or skipped
        if from_state == cls.TASK_BLOCKED:
            return to_state in {cls.TASK_PENDING, cls.TASK_SKIPPED}

        # Gate rejected can go back to pending (revision loop)
        if from_state == cls.GATE_REJECTED:
            return to_state == cls.GATE_PENDING

        # Terminal states stay terminal
        if cls.is_terminal(from_state):
            return False

        return False


class NodeInstance:
    """Mutable runtime state for a node in a session.

    This is the ONLY runtime state persisted.
    Node definition is read from the snapshot at runtime.

    The separation ensures:
    1. Session data stays small (only runtime state)
    2. The snapshot is the single source of structural truth
    3. Reproducibility (same snapshot_hash = same structure)
    """

    __slots__ = (
        "node_id",
        "state",
        "attempt",
        "ready_at",
        "started_at",
        "ended_at",
        "blocked_reason",
        "failure_kind",
        "error_message",
        "model_name",
        "agent_name",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cost_usd",
    )

    def __init__(
        self,
        node_id: str,
        state: NodeState = NodeState.TASK_PENDING,
        attempt: int = 0,
        ready_at: datetime | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        blocked_reason: str | None = None,
        failure_kind: str | None = None,
        error_message: str | None = None,
        model_name: str | None = None,
        agent_name: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        cost_usd: float = 0.0,
    ):
        """Initialize a node instance.

        Args:
            node_id: References Node.id in snapshot
            state: Runtime state enum
            attempt: Retry/loop iteration count
            ready_at: When node became ready to execute
            started_at: When execution started
            ended_at: When execution ended
            blocked_reason: Human-readable reason for blocked state
            failure_kind: "transient" or "fatal" (if failed)
            error_message: Error message (if failed)
            model_name: AI model name that will execute this node
            agent_name: Agent name that will execute this node
            input_tokens: Number of input tokens consumed
            output_tokens: Number of output tokens generated
            total_tokens: Total token count (input + output)
            cost_usd: Cost in USD for this node execution
        """
        self.node_id = node_id
        self.state = state
        self.attempt = attempt
        self.ready_at = ready_at
        self.started_at = started_at
        self.ended_at = ended_at
        self.blocked_reason = blocked_reason
        self.failure_kind = failure_kind
        self.error_message = error_message
        self.model_name = model_name
        self.agent_name = agent_name
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.cost_usd = cost_usd

    def transition_to(self, new_state: NodeState) -> bool:
        """Transition to a new state if valid.

        Returns:
            True if transition was valid and applied
        """
        if not NodeState.can_transition_to(self.state, new_state):
            return False

        self.state = new_state

        if new_state == NodeState.TASK_RUNNING:
            self.started_at = datetime.now()
        elif NodeState.is_terminal(new_state):
            self.ended_at = datetime.now()

        return True

    def increment_attempt(self) -> None:
        """Increment attempt counter (for retries/loops)."""
        self.attempt += 1

    def set_blocked(self, reason: str) -> None:
        """Set node to blocked state with reason via transition_to."""
        self.blocked_reason = reason
        if not self.transition_to(NodeState.TASK_BLOCKED):
            # Force for cases where the state machine doesn't have an explicit edge
            self.state = NodeState.TASK_BLOCKED

    def set_failed(self, failure_kind: str = "transient", error: str | None = None) -> None:
        """Set node to failed state via transition_to."""
        self.failure_kind = failure_kind
        self.error_message = error
        if not self.transition_to(NodeState.TASK_FAILED):
            # Force for cases where the state machine doesn't have an explicit edge
            self.state = NodeState.TASK_FAILED
            self.ended_at = datetime.now()

    def mark_ready(self) -> None:
        """Mark node as ready to execute."""
        self.state = NodeState.TASK_PENDING
        self.ready_at = datetime.now()

    def update_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """Update token usage for this node execution.

        Args:
            input_tokens: Number of input tokens consumed
            output_tokens: Number of output tokens generated
            cost_usd: Cost in USD for this execution
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens
        self.cost_usd += cost_usd

    @property
    def is_terminal(self) -> bool:
        """Check if this instance is in a terminal state."""
        return NodeState.is_terminal(self.state)

    @property
    def is_active(self) -> bool:
        """Check if this instance is currently executing."""
        return NodeState.is_active(self.state)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate execution duration."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "attempt": self.attempt,
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "blocked_reason": self.blocked_reason,
            "failure_kind": self.failure_kind,
            "error_message": self.error_message,
            "model_name": self.model_name,
            "agent_name": self.agent_name,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodeInstance":
        """Create from dictionary."""
        state_str = data.get("state", "task_pending")
        try:
            state = NodeState(state_str)
        except ValueError:
            state = NodeState.TASK_PENDING

        def parse_dt(s: str | None) -> datetime | None:
            if s:
                try:
                    return datetime.fromisoformat(s)
                except (ValueError, TypeError):
                    return None
            return None

        return cls(
            node_id=data["node_id"],
            state=state,
            attempt=data.get("attempt", 0),
            ready_at=parse_dt(data.get("ready_at")),
            started_at=parse_dt(data.get("started_at")),
            ended_at=parse_dt(data.get("ended_at")),
            blocked_reason=data.get("blocked_reason"),
            failure_kind=data.get("failure_kind"),
            error_message=data.get("error_message"),
            model_name=data.get("model_name"),
            agent_name=data.get("agent_name"),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost_usd=data.get("cost_usd", 0.0),
        )
