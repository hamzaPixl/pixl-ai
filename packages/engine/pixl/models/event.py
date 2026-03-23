"""Event models for workflow execution logging.

Events form an append-only log of everything that happens during
workflow execution. Each transition, state change, or action produces
an event. This provides a complete audit trail and enables debugging,
replay, and analysis.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Types of events in the workflow execution log."""

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_STARTED = "session_started"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    SESSION_RECLAIMED = "session_reclaimed"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    SESSION_CANCELLED = "session_cancelled"

    # Task events
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"
    TASK_BLOCKED = "task_blocked"
    TASK_UNBLOCKED = "task_unblocked"
    TASK_RETRY_QUEUED = "task_retry_queued"
    TASK_PAUSED = "task_paused"
    TASK_ROLLED_BACK = "task_rolled_back"

    # Gate events
    GATE_REQUESTED = "gate_requested"
    GATE_APPROVED = "gate_approved"
    GATE_REJECTED = "gate_rejected"
    GATE_TIMEOUT = "gate_timeout"

    # Artifact events
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_MODIFIED = "artifact_modified"

    LOOP_ITERATION = "loop_iteration"
    LOOP_MAX_REACHED = "loop_max_reached"
    LOOP_EXHAUSTION_WARNING = "loop_exhaustion_warning"

    # Contract events
    CONTRACT_VIOLATION = "contract_violation"
    CONTRACT_WARNING = "contract_warning"
    CONTRACT_PASSED = "contract_passed"
    GIT_UNAVAILABLE = "git_unavailable"

    # Frozen artifact events (kept for backward compat, new code uses ARTIFACT_CHANGED)
    ARTIFACT_FROZEN = "artifact_frozen"
    FROZEN_ARTIFACT_VIOLATED = "frozen_artifact_violated"
    FROZEN_ARTIFACT_UPDATED = "frozen_artifact_updated"

    # Merged artifact event (replaces ARTIFACT_CREATED + ARTIFACT_MODIFIED + ARTIFACT_FROZEN)
    ARTIFACT_CHANGED = "artifact_changed"

    # Entity lifecycle events
    ENTITY_STATUS_CHANGED = "entity_status_changed"

    # Entity CRUD events
    FEATURE_CREATED = "feature_created"
    FEATURE_UPDATED = "feature_updated"
    FEATURE_DELETED = "feature_deleted"
    EPIC_CREATED = "epic_created"
    EPIC_UPDATED = "epic_updated"
    ROADMAP_CREATED = "roadmap_created"
    ROADMAP_UPDATED = "roadmap_updated"
    MILESTONE_CREATED = "milestone_created"

    # Autonomy events
    AUTONOMY_CHANGED = "autonomy_changed"

    # System events
    CHECKPOINT_SAVED = "checkpoint_saved"
    ERROR = "error"

    # Recovery events
    RECOVERY_REQUESTED = "recovery_requested"
    RECOVERY_DECISION = "recovery_decision"
    RECOVERY_SUCCEEDED = "recovery_succeeded"
    RECOVERY_FAILED = "recovery_failed"
    RECOVERY_ESCALATED = "recovery_escalated"
    RECOVERY_NO_RUNNABLE_NODE = "recovery_no_runnable_node"
    RECOVERY_ACTION = "recovery_action"  # Coarse-grained recovery event

    # Structured output events
    STRUCTURED_OUTPUT_PARSED = "structured_output_parsed"
    STRUCTURED_OUTPUT_INVALID = "structured_output_invalid"

    # Artifact handoff events
    ARTIFACT_HANDOFF = "artifact_handoff"

    # Budget events
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"

    # SDK-level events (transient — streamed via WS but NOT persisted to events table)
    SDK_QUERY_STARTED = "sdk_query_started"
    SDK_QUERY_COMPLETED = "sdk_query_completed"
    SDK_TOOL_CALL_STARTED = "sdk_tool_call_started"
    SDK_TOOL_CALL_COMPLETED = "sdk_tool_call_completed"
    SDK_THINKING_STARTED = "sdk_thinking_started"
    SDK_THINKING_COMPLETED = "sdk_thinking_completed"
    SDK_TEXT_DELTA = "sdk_text_delta"
    SDK_ERROR = "sdk_error"


# SDK events are streamed via WS as transient messages but NOT persisted to DB.
TRANSIENT_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EventType.SDK_QUERY_STARTED,
        EventType.SDK_QUERY_COMPLETED,
        EventType.SDK_TOOL_CALL_STARTED,
        EventType.SDK_TOOL_CALL_COMPLETED,
        EventType.SDK_THINKING_STARTED,
        EventType.SDK_THINKING_COMPLETED,
        EventType.SDK_TEXT_DELTA,
        EventType.SDK_ERROR,
    }
)


class Event(BaseModel):
    """A single event in the workflow execution log.

    Events are immutable and form an append-only log.
    The event log (SQLite ``events`` table) provides a complete audit trail.
    """

    id: str = Field(
        default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}",
        description="Unique event ID",
    )
    type: EventType = Field(description="Event type")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    session_id: str = Field(description="Session ID")

    # Event-specific references
    node_id: str | None = Field(default=None, description="Associated node ID")
    artifact_id: str | None = Field(default=None, description="Associated artifact ID")

    # Event-specific data
    data: dict[str, Any] = Field(default_factory=dict, description="Flexible data payload")

    @classmethod
    def create(
        cls,
        event_type: EventType,
        session_id: str,
        node_id: str | None = None,
        artifact_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> "Event":
        """Create a new event.

        Args:
            event_type: Type of event
            session_id: Session ID
            node_id: Associated node ID (optional)
            artifact_id: Associated artifact ID (optional)
            data: Event-specific data

        Returns:
            New Event instance
        """
        return cls(
            type=event_type,
            session_id=session_id,
            node_id=node_id,
            artifact_id=artifact_id,
            data=data or {},
        )

    @classmethod
    def session_created(cls, session_id: str, data: dict[str, Any] | None = None) -> "Event":
        """Create a session_created event."""
        return cls.create(EventType.SESSION_CREATED, session_id, data=data)

    @classmethod
    def session_started(cls, session_id: str) -> "Event":
        """Create a session_started event."""
        return cls.create(EventType.SESSION_STARTED, session_id)

    @classmethod
    def session_paused(cls, session_id: str, reason: str | None = None) -> "Event":
        """Create a session_paused event."""
        return cls.create(EventType.SESSION_PAUSED, session_id, data={"reason": reason})

    @classmethod
    def session_resumed(cls, session_id: str) -> "Event":
        """Create a session_resumed event."""
        return cls.create(EventType.SESSION_RESUMED, session_id)

    @classmethod
    def session_reclaimed(
        cls,
        session_id: str,
        *,
        reason: str,
        previous_owner_pid: int | None = None,
        staleness_age_seconds: float | None = None,
    ) -> "Event":
        """Create a session_reclaimed event."""
        data: dict[str, Any] = {"reason": reason}
        if previous_owner_pid is not None:
            data["previous_owner_pid"] = previous_owner_pid
        if staleness_age_seconds is not None:
            data["staleness_age_seconds"] = staleness_age_seconds
        return cls.create(EventType.SESSION_RECLAIMED, session_id, data=data)

    @classmethod
    def session_completed(cls, session_id: str, data: dict[str, Any] | None = None) -> "Event":
        """Create a session_completed event."""
        return cls.create(EventType.SESSION_COMPLETED, session_id, data=data)

    @classmethod
    def session_failed(cls, session_id: str, error: str) -> "Event":
        """Create a session_failed event."""
        return cls.create(EventType.SESSION_FAILED, session_id, data={"error": error})

    @classmethod
    def session_cancelled(cls, session_id: str, reason: str | None = None) -> "Event":
        """Create a session_cancelled event."""
        return cls.create(EventType.SESSION_CANCELLED, session_id, data={"reason": reason})

    @classmethod
    def task_started(
        cls,
        session_id: str,
        node_id: str,
        agent_name: str | None = None,
        effective_model: str | None = None,
    ) -> "Event":
        """Create a task_started event."""
        data = {}
        if agent_name:
            data["agent_name"] = agent_name
        if effective_model:
            data["effective_model"] = effective_model
        return cls.create(EventType.TASK_STARTED, session_id, node_id=node_id, data=data)

    @classmethod
    def task_completed(
        cls,
        session_id: str,
        node_id: str,
        duration_seconds: float | None = None,
        usage: dict[str, int | float] | None = None,
    ) -> "Event":
        """Create a task_completed event with optional token usage data.

        Args:
            session_id: Session ID
            node_id: Node ID
            duration_seconds: Task execution duration
            usage: Token usage dict with keys: input_tokens, output_tokens, total_tokens, cost_usd
        """
        data: dict[str, Any] = {}
        if duration_seconds is not None:
            data["duration_seconds"] = duration_seconds
        if usage is not None:
            data["usage"] = usage

        return cls.create(
            EventType.TASK_COMPLETED,
            session_id,
            node_id=node_id,
            data=data,
        )

    @classmethod
    def task_failed(
        cls,
        session_id: str,
        node_id: str,
        error: str,
        failure_kind: str = "transient",
        error_type: str | None = None,
        error_metadata: dict[str, Any] | None = None,
    ) -> "Event":
        """Create a task_failed event."""
        data: dict[str, Any] = {"error": error, "failure_kind": failure_kind}
        if error_type:
            data["error_type"] = error_type
        if error_metadata:
            data["error_metadata"] = error_metadata
        return cls.create(
            EventType.TASK_FAILED,
            session_id,
            node_id=node_id,
            data=data,
        )

    @classmethod
    def task_blocked(cls, session_id: str, node_id: str, reason: str) -> "Event":
        """Create a task_blocked event."""
        return cls.create(
            EventType.TASK_BLOCKED,
            session_id,
            node_id=node_id,
            data={"reason": reason},
        )

    @classmethod
    def task_retry_queued(cls, session_id: str, node_id: str, attempt: int) -> "Event":
        """Create a task_retry_queued event."""
        return cls.create(
            EventType.TASK_RETRY_QUEUED,
            session_id,
            node_id=node_id,
            data={"attempt": attempt},
        )

    @classmethod
    def gate_requested(cls, session_id: str, node_id: str, artifacts: list[str]) -> "Event":
        """Create a gate_requested event."""
        return cls.create(
            EventType.GATE_REQUESTED,
            session_id,
            node_id=node_id,
            data={"artifacts": artifacts},
        )

    @classmethod
    def gate_approved(cls, session_id: str, node_id: str, approver: str | None = None) -> "Event":
        """Create a gate_approved event."""
        return cls.create(
            EventType.GATE_APPROVED,
            session_id,
            node_id=node_id,
            data={"approver": approver},
        )

    @classmethod
    def gate_rejected(cls, session_id: str, node_id: str, reason: str | None = None) -> "Event":
        """Create a gate_rejected event."""
        return cls.create(
            EventType.GATE_REJECTED,
            session_id,
            node_id=node_id,
            data={"reason": reason},
        )

    @classmethod
    def gate_timeout(cls, session_id: str, node_id: str, timeout_minutes: int) -> "Event":
        """Create a gate_timeout event."""
        return cls.create(
            EventType.GATE_TIMEOUT,
            session_id,
            node_id=node_id,
            data={"timeout_minutes": timeout_minutes},
        )

    @classmethod
    def checkpoint_saved(cls, session_id: str, data: dict[str, Any] | None = None) -> "Event":
        """Create a checkpoint_saved event."""
        return cls.create(EventType.CHECKPOINT_SAVED, session_id, data=data)

    @classmethod
    def error(
        cls,
        session_id: str,
        *,
        message: str,
        error_type: str,
        node_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        is_transient: bool | None = None,
        cause: str | None = None,
    ) -> "Event":
        """Create an error event."""
        data: dict[str, Any] = {
            "message": message,
            "error_type": error_type,
            "metadata": metadata or {},
        }
        if is_transient is not None:
            data["is_transient"] = is_transient
        if cause:
            data["cause"] = cause
        return cls.create(
            EventType.ERROR,
            session_id,
            node_id=node_id,
            data=data,
        )

    @classmethod
    def artifact_created(
        cls, session_id: str, artifact_id: str, node_id: str | None = None
    ) -> "Event":
        """Create an artifact_created event."""
        return cls.create(
            EventType.ARTIFACT_CREATED,
            session_id,
            node_id=node_id,
            artifact_id=artifact_id,
        )

    @classmethod
    def loop_iteration(
        cls, session_id: str, loop_id: str, iteration: int, from_node: str, to_node: str
    ) -> "Event":
        """Create a loop_iteration event."""
        return cls.create(
            EventType.LOOP_ITERATION,
            session_id,
            data={
                "loop_id": loop_id,
                "iteration": iteration,
                "from": from_node,
                "to": to_node,
            },
        )

    @classmethod
    def loop_max_reached(cls, session_id: str, loop_id: str, max_iterations: int) -> "Event":
        """Create a loop_max_reached event."""
        return cls.create(
            EventType.LOOP_MAX_REACHED,
            session_id,
            data={"loop_id": loop_id, "max_iterations": max_iterations},
        )

    @classmethod
    def loop_exhaustion_warning(
        cls,
        session_id: str,
        loop_id: str,
        from_node: str,
        max_iterations: int,
        message: str,
    ) -> "Event":
        """Create a loop_exhaustion_warning event for autonomous mode continuation."""
        return cls.create(
            EventType.LOOP_EXHAUSTION_WARNING,
            session_id,
            data={
                "loop_id": loop_id,
                "from_node": from_node,
                "max_iterations": max_iterations,
                "message": message,
            },
        )

    @classmethod
    def contract_violation(
        cls,
        session_id: str,
        node_id: str,
        violations: list[str],
    ) -> "Event":
        """Create a contract_violation event."""
        return cls.create(
            EventType.CONTRACT_VIOLATION,
            session_id,
            node_id=node_id,
            data={"violations": violations},
        )

    @classmethod
    def contract_warning(
        cls,
        session_id: str,
        node_id: str,
        warning: str,
    ) -> "Event":
        """Create a contract_warning event."""
        return cls.create(
            EventType.CONTRACT_WARNING,
            session_id,
            node_id=node_id,
            data={"warning": warning},
        )

    @classmethod
    def contract_passed(cls, session_id: str, node_id: str) -> "Event":
        """Create a contract_passed event."""
        return cls.create(
            EventType.CONTRACT_PASSED,
            session_id,
            node_id=node_id,
        )

    @classmethod
    def git_unavailable(
        cls,
        session_id: str,
        node_id: str,
        check: str,
    ) -> "Event":
        """Create a git_unavailable event (auditable skip)."""
        return cls.create(
            EventType.GIT_UNAVAILABLE,
            session_id,
            node_id=node_id,
            data={"check": check},
        )

    @classmethod
    def artifact_frozen(
        cls,
        session_id: str,
        node_id: str,
        path: str,
        sha256: str,
    ) -> "Event":
        """Create an artifact_frozen event."""
        return cls.create(
            EventType.ARTIFACT_FROZEN,
            session_id,
            node_id=node_id,
            data={"path": path, "sha256": sha256},
        )

    @classmethod
    def frozen_artifact_violated(
        cls,
        session_id: str,
        node_id: str,
        path: str,
        expected_hash: str,
        actual_hash: str | None,
    ) -> "Event":
        """Create a frozen_artifact_violated event."""
        return cls.create(
            EventType.FROZEN_ARTIFACT_VIOLATED,
            session_id,
            node_id=node_id,
            data={
                "path": path,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
            },
        )

    @classmethod
    def frozen_artifact_updated(
        cls,
        session_id: str,
        node_id: str,
        path: str,
        old_hash: str,
        new_hash: str,
    ) -> "Event":
        """Create a frozen_artifact_updated event (change request approved)."""
        return cls.create(
            EventType.FROZEN_ARTIFACT_UPDATED,
            session_id,
            node_id=node_id,
            data={
                "path": path,
                "old_hash": old_hash,
                "new_hash": new_hash,
            },
        )

    @classmethod
    def entity_status_changed(
        cls,
        session_id: str,
        entity_id: str,
        from_status: str,
        to_status: str,
        stage_id: str | None = None,
        trigger: str = "workflow",
    ) -> "Event":
        """Create an entity_status_changed event.

        Emitted when a feature/epic/roadmap transitions status,
        typically triggered by a workflow stage completion.
        """
        return cls.create(
            EventType.ENTITY_STATUS_CHANGED,
            session_id,
            node_id=stage_id,
            data={
                "entity_id": entity_id,
                "from_status": from_status,
                "to_status": to_status,
                "trigger": trigger,
            },
        )

    # Structured Output Events

    @classmethod
    def structured_output_parsed(
        cls,
        session_id: str,
        node_id: str,
        content_hash: str,
        summary_count: int = 0,
        artifact_count: int = 0,
    ) -> "Event":
        """Create a structured_output_parsed event."""
        return cls.create(
            EventType.STRUCTURED_OUTPUT_PARSED,
            session_id,
            node_id=node_id,
            data={
                "content_hash": content_hash,
                "summary_count": summary_count,
                "artifact_count": artifact_count,
            },
        )

    @classmethod
    def structured_output_invalid(
        cls,
        session_id: str,
        node_id: str,
        error: str,
    ) -> "Event":
        """Create a structured_output_invalid event."""
        return cls.create(
            EventType.STRUCTURED_OUTPUT_INVALID,
            session_id,
            node_id=node_id,
            data={"error": error},
        )

    # SDK-Level Events (for real-time tracing)

    @classmethod
    def sdk_query_started(
        cls,
        session_id: str,
        node_id: str,
        model: str,
        prompt_preview: str | None = None,
    ) -> "Event":
        """Create an sdk_query_started event when an LLM query begins."""
        return cls.create(
            EventType.SDK_QUERY_STARTED,
            session_id,
            node_id=node_id,
            data={
                "model": model,
                "prompt_preview": (prompt_preview[:200] + "...")
                if prompt_preview and len(prompt_preview) > 200
                else prompt_preview,
            },
        )

    @classmethod
    def sdk_query_completed(
        cls,
        session_id: str,
        node_id: str,
        duration_seconds: float,
        num_turns: int | None = None,
        total_tokens: int | None = None,
        usage: dict[str, int | float] | None = None,
    ) -> "Event":
        """Create an sdk_query_completed event when an LLM query finishes.

        Args:
            session_id: Session ID
            node_id: Node ID
            duration_seconds: Query execution duration
            num_turns: Number of turns in the conversation
            total_tokens: Total token count (for backward compatibility)
            usage: Detailed token usage dict with keys: input_tokens, output_tokens, total_tokens, cost_usd
        """
        data: dict[str, Any] = {"duration_seconds": duration_seconds}
        if num_turns is not None:
            data["num_turns"] = num_turns
        if total_tokens is not None:
            data["total_tokens"] = total_tokens
        if usage is not None:
            data["usage"] = usage
            if total_tokens is None and "total_tokens" in usage:
                data["total_tokens"] = usage["total_tokens"]

        return cls.create(
            EventType.SDK_QUERY_COMPLETED,
            session_id,
            node_id=node_id,
            data=data,
        )

    @classmethod
    def sdk_tool_call_started(
        cls,
        session_id: str,
        node_id: str,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
    ) -> "Event":
        """Create an sdk_tool_call_started event when a tool begins execution."""
        return cls.create(
            EventType.SDK_TOOL_CALL_STARTED,
            session_id,
            node_id=node_id,
            data={
                "tool_name": tool_name,
                "tool_input": tool_input or {},
            },
        )

    @classmethod
    def sdk_tool_call_completed(
        cls,
        session_id: str,
        node_id: str,
        tool_name: str,
        is_error: bool = False,
        error_message: str | None = None,
    ) -> "Event":
        """Create an sdk_tool_call_completed event when a tool finishes."""
        data: dict[str, Any] = {"tool_name": tool_name, "is_error": is_error}
        if error_message:
            data["error_message"] = error_message
        return cls.create(
            EventType.SDK_TOOL_CALL_COMPLETED,
            session_id,
            node_id=node_id,
            data=data,
        )

    @classmethod
    def sdk_thinking_started(
        cls,
        session_id: str,
        node_id: str,
    ) -> "Event":
        """Create an sdk_thinking_started event when extended thinking begins."""
        return cls.create(
            EventType.SDK_THINKING_STARTED,
            session_id,
            node_id=node_id,
        )

    @classmethod
    def sdk_thinking_completed(
        cls,
        session_id: str,
        node_id: str,
        thinking_preview: str | None = None,
    ) -> "Event":
        """Create an sdk_thinking_completed event when extended thinking ends."""
        return cls.create(
            EventType.SDK_THINKING_COMPLETED,
            session_id,
            node_id=node_id,
            data={
                "thinking_preview": (thinking_preview[:200] + "...")
                if thinking_preview and len(thinking_preview) > 200
                else thinking_preview,
            },
        )

    @classmethod
    def sdk_text_delta(
        cls,
        session_id: str,
        node_id: str,
        text: str,
    ) -> "Event":
        """Create an sdk_text_delta event for streaming text output."""
        return cls.create(
            EventType.SDK_TEXT_DELTA,
            session_id,
            node_id=node_id,
            data={"text": text},
        )

    @classmethod
    def sdk_error(
        cls,
        session_id: str,
        node_id: str,
        error: str,
        error_type: str | None = None,
    ) -> "Event":
        """Create an sdk_error event when an SDK-level error occurs."""
        data: dict[str, Any] = {"error": error}
        if error_type:
            data["error_type"] = error_type
        return cls.create(
            EventType.SDK_ERROR,
            session_id,
            node_id=node_id,
            data=data,
        )

    @classmethod
    def artifact_handoff(
        cls,
        session_id: str,
        node_id: str,
        payload: dict[str, Any] | None = None,
    ) -> "Event":
        """Create an artifact_handoff event before task execution.

        Payload should include manifest and context used for required artifact
        handoff validation.
        """
        data: dict[str, Any] = payload or {}
        return cls.create(
            EventType.ARTIFACT_HANDOFF,
            session_id,
            node_id=node_id,
            data=data,
        )
