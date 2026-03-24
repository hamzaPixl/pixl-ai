"""Workflow session models for tracking workflow execution.

This module contains the WorkflowSession and supporting models for
graph-based workflow orchestration:
- NodeInstance for runtime state
- ExecutorCursor for precise checkpointing
- SessionStatus (DERIVED, not stored)
"""

import logging
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, computed_field

if TYPE_CHECKING:
    from pixl.models.workflow import WorkflowSnapshot

logger = logging.getLogger(__name__)


class SessionStatus(StrEnum):
    """Status of a workflow session.

    This is DERIVED from node states at runtime, NOT stored directly.
    The @computed_field in WorkflowSession calculates this from node_instances.
    """

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STALLED = "stalled"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# If heartbeat_at/last_updated_at is older than this threshold and no nodes
# are active, the session is considered stalled (zombie detection).
# Reduced from 150s to 60s thanks to heartbeat run liveness tracking.
STALENESS_THRESHOLD_SECONDS = 60


class ExecutorCursor(BaseModel):
    """Precise checkpoint for session resumption.

    The cursor tracks exactly where execution is so resuming is deterministic.
    This ensures we don't have non-deterministic behavior when multiple nodes
    become ready simultaneously.
    """

    current_node_id: str | None = Field(default=None, description="Node currently being executed")
    ready_queue: list[str] = Field(
        default_factory=list,
        description="Node IDs ready to execute (SORTED for determinism)",
    )
    last_event_id: str | None = Field(
        default=None, description="Last event ID written to event log"
    )

    def add_to_ready_queue(self, node_id: str) -> None:
        """Add a node to the ready queue (maintains sorted order)."""
        if node_id not in self.ready_queue:
            self.ready_queue.append(node_id)
            self.ready_queue.sort()  # Deterministic ordering

    def remove_from_ready_queue(self, node_id: str) -> None:
        """Remove a node from the ready queue."""
        if node_id in self.ready_queue:
            self.ready_queue.remove(node_id)

    def get_next_ready(self) -> str | None:
        """Get the next node from the ready queue."""
        return self.ready_queue[0] if self.ready_queue else None

    def has_ready(self) -> bool:
        """Check if there are nodes ready to execute."""
        return len(self.ready_queue) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_node_id": self.current_node_id,
            "ready_queue": self.ready_queue,
            "last_event_id": self.last_event_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutorCursor":
        """Create from dictionary."""
        return cls.model_validate(data)


class LoopState(BaseModel):
    """State for a single loop in a session.

    Tracks loop iterations and enforces max iteration limits.
    """

    current_iteration: int = Field(default=0, description="Current iteration count")
    max_iterations: int = Field(default=3, description="Maximum iterations allowed")
    history: list[dict] = Field(default_factory=list, description="Iteration history")

    def can_enter(self) -> bool:
        """Check if loop can be entered again."""
        return self.current_iteration < self.max_iterations

    def record_iteration(self, from_node: str, to_node: str, via_edge: str) -> None:
        """Record entering a loop iteration.

        Triggered when executor TRAVERSES a loop edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID (loop back to)
            via_edge: Edge trigger type
        """
        self.current_iteration += 1
        self.history.append(
            {
                "iteration": self.current_iteration,
                "from": from_node,
                "to": to_node,
                "via": via_edge,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoopState":
        """Create from dictionary."""
        return cls.model_validate(data)


def create_node_instance(
    node_id: str,
    state: str = "task_pending",
    *,
    ready_at: str | None = None,
    model_name: str | None = None,
    agent_name: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> dict:
    """Factory for node instance dicts — single source of truth for the schema.

    Args:
        node_id: Unique identifier for the node
        state: Current state (default: task_pending)
        ready_at: ISO timestamp; defaults to now
        model_name: Resolved model name (optional)
        agent_name: Agent name (optional)
        input_tokens: Input tokens consumed
        output_tokens: Output tokens generated
        cost_usd: Cost in USD
    """
    instance: dict = {
        "node_id": node_id,
        "state": state,
        "attempt": 0,
        "ready_at": ready_at or datetime.now().isoformat(),
        "started_at": None,
        "ended_at": None,
        "blocked_reason": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": cost_usd,
    }
    if model_name is not None:
        instance["model_name"] = model_name
    if agent_name is not None:
        instance["agent_name"] = agent_name
    return instance


class WorkflowSession(BaseModel):
    """A workflow execution session.

    This represents ONE instance of a workflow template run on a feature.
    It contains:
    - Runtime state only (node_instances, loop_state)
    - Reference to snapshot (via snapshot_hash)
    - Executor cursor for resumption

    The status is DERIVED from node_instances at runtime, NOT stored.
    """

    # Schema versioning
    session_schema_version: int = Field(default=1, description="Session schema version")

    # Identity
    id: str = Field(description="Session ID (sess-XXXX)")
    feature_id: str = Field(description="Associated feature ID")
    snapshot_hash: str = Field(description="Hash of WorkflowSnapshot being executed")

    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None, description="When execution started")
    ended_at: datetime | None = Field(default=None, description="When execution ended")
    last_updated_at: datetime | None = Field(default=None, description="Last state change")
    paused_at: datetime | None = Field(
        default=None, description="When session was explicitly paused"
    )
    pause_reason: str | None = Field(default=None, description="Reason for explicit pause")

    # Runtime state (mutable, persisted)
    node_instances: dict[str, dict] = Field(
        default_factory=dict,
        description="NodeInstance state (as dict for JSON)",
    )
    loop_state: dict[str, dict] = Field(default_factory=dict, description="LoopState by loop_id")
    executor_cursor: ExecutorCursor | None = Field(default=None, description="Execution checkpoint")

    # Git baseline (set at session creation for contract validation)
    baseline_commit: str | None = Field(
        default=None, description="Git commit hash at workflow start"
    )
    workspace_root: str | None = Field(
        default=None, description="Absolute path to git workspace root"
    )

    # Frozen artifacts (path -> SHA256 hash, set at gate approval)
    frozen_artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Frozen artifact paths to SHA256 hashes",
    )

    # Artifacts
    artifacts: list[dict] = Field(
        default_factory=list, description="ArtifactMetadata (as dict for JSON)"
    )

    # Structured outputs (for context_mode: structured)
    structured_outputs: dict[str, dict] = Field(
        default_factory=dict,
        description="Parsed StageOutput per node_id (as JSON-serializable dicts).",
    )
    session_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Small executor metadata replacing baton in structured mode.",
    )

    # Stored status (authoritative, updated on every mutation)
    stored_status: str | None = Field(
        default=None,
        description="Stored status from DB. When set, takes precedence over computed status.",
    )

    # Current heartbeat run
    current_run_id: str | None = Field(default=None, description="Active heartbeat run ID")

    # Baton context (for context_mode: baton)
    baton: dict | None = Field(
        default=None,
        description="Current baton state as JSON-serializable dict. None in classic mode.",
    )
    baton_history: list[dict] = Field(
        default_factory=list,
        description="Baton snapshots after each stage (for audit trail).",
    )
    context_audit: list[dict] = Field(
        default_factory=list,
        description="Context compiler audit entries (what was included per stage and why).",
    )

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        """Convert to int with deterministic fallback."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _is_terminal_failed_node(cls, node: dict[str, Any]) -> bool:
        """True when a failed node should mark the session as failed."""
        from pixl.models.node_instance import NodeState

        if node.get("state") != NodeState.TASK_FAILED.value:
            return False
        if node.get("failure_kind") == "fatal":
            return True
        attempt_i = cls._coerce_int(node.get("attempt", 0), 0)
        max_attempts_i = max(1, cls._coerce_int(node.get("max_attempts", 3), 3))
        threshold = max(max_attempts_i - 1, 0)
        return attempt_i >= threshold

    @staticmethod
    def _gate_has_revision_loop(snapshot: "WorkflowSnapshot", gate_id: str) -> bool:
        """Return True when the rejected gate has a failure-edge revision loop."""
        for constraint in snapshot.graph.loop_constraints:
            if constraint.from_node == gate_id and constraint.edge_trigger.value == "failure":
                return True
        return False

    # Status (DERIVED, NOT stored in JSON)
    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> SessionStatus:
        """Derive status from node states.

        Algorithm (ordered by priority):
        1. Any gate waiting? → PAUSED
        2. Any task running? → RUNNING
        3. Any task failed and NOT retryable? → FAILED
        4. All exit nodes in terminal success states? → COMPLETED
        5. Otherwise → RUNNING (can still progress)

        This is computed at runtime, not stored directly.
        """
        from pixl.models.node_instance import NodeState

        # Import here to avoid circular dependency
        if not self.node_instances:
            return SessionStatus.CREATED

        # Explicit pause via CLI
        if self.paused_at:
            return SessionStatus.PAUSED

        node_states = list(self._get_node_instance_values())

        # 1. Gate waiting = paused
        if any(n.get("state") == NodeState.GATE_WAITING.value for n in node_states):
            return SessionStatus.PAUSED
        if any(n.get("state") == NodeState.TASK_BLOCKED.value for n in node_states):
            return SessionStatus.PAUSED

        # 2. Task running = active
        if any(n.get("state") == NodeState.TASK_RUNNING.value for n in node_states):
            return SessionStatus.RUNNING

        # 3. Check for fatal failure (not retryable)
        for n in node_states:
            if self._is_terminal_failed_node(n):
                return SessionStatus.FAILED

        if any(n.get("state") == NodeState.GATE_REJECTED.value for n in node_states):
            return SessionStatus.FAILED

        # 4. Check if all exit nodes are in terminal success states
        # (This requires loading snapshot - simplified here)
        terminal_success = {
            NodeState.TASK_COMPLETED.value,
            NodeState.GATE_APPROVED.value,
            NodeState.TASK_SKIPPED.value,
        }

        # If we have nodes and all are in terminal states, check ended_at.
        # Without ended_at, downstream nodes may not have instances yet.
        if (
            self.ended_at
            and node_states
            and all(n.get("state") in terminal_success for n in node_states)
        ):
            return SessionStatus.COMPLETED

        # 5. ended_at is set but not all nodes succeeded → FAILED
        #    (e.g. session was forcibly ended, timed out, or ended mid-run)
        if self.ended_at:
            return SessionStatus.FAILED

        # 6. Staleness detection — no active nodes and last_updated_at is stale
        if self.last_updated_at:
            elapsed = (datetime.now() - self.last_updated_at).total_seconds()
            if elapsed > STALENESS_THRESHOLD_SECONDS:
                return SessionStatus.STALLED

        # 7. Can still progress
        return SessionStatus.RUNNING

    def compute_status_with_snapshot(self, snapshot: "WorkflowSnapshot | None") -> SessionStatus:
        """Derive status from node states and optional snapshot.

        Args:
            snapshot: Optional WorkflowSnapshot to get total node count.
                      If provided, ensures all graph nodes are complete
                      before marking as COMPLETED.

        Returns:
            The current SessionStatus
        """
        from pixl.models.node_instance import NodeState

        # Import here to avoid circular dependency
        if not self.node_instances:
            return SessionStatus.CREATED

        # Explicit pause via CLI
        if self.paused_at:
            return SessionStatus.PAUSED

        node_states = list(self._get_node_instance_values())

        # 1. Gate waiting = paused
        if any(n.get("state") == NodeState.GATE_WAITING.value for n in node_states):
            return SessionStatus.PAUSED
        if any(n.get("state") == NodeState.TASK_BLOCKED.value for n in node_states):
            return SessionStatus.PAUSED

        # 2. Task running = active
        if any(n.get("state") == NodeState.TASK_RUNNING.value for n in node_states):
            return SessionStatus.RUNNING

        # 3. Check for fatal failure (not retryable)
        for n in node_states:
            if self._is_terminal_failed_node(n):
                return SessionStatus.FAILED

        rejected_gate_ids: list[str] = [
            str(n.get("node_id"))
            for n in node_states
            if n.get("state") == NodeState.GATE_REJECTED.value and n.get("node_id")
        ]
        if rejected_gate_ids:
            # Rejected gates are terminal unless they have configured revision loops.
            if snapshot is None:
                return SessionStatus.FAILED
            if any(
                not self._gate_has_revision_loop(snapshot, gate_id) for gate_id in rejected_gate_ids
            ):
                return SessionStatus.FAILED

        # 4. Check if all nodes are in terminal success states
        terminal_success = {
            NodeState.TASK_COMPLETED.value,
            NodeState.GATE_APPROVED.value,
            NodeState.TASK_SKIPPED.value,
        }

        # If snapshot provided, check ALL nodes in graph (not just instances)
        if snapshot is not None:
            total_node_count = len(snapshot.graph.nodes)
            completed_count = sum(1 for n in node_states if n.get("state") in terminal_success)
            # Only complete if all nodes have instances and are in terminal states
            if completed_count == total_node_count:
                return SessionStatus.COMPLETED
        else:
            # Without snapshot, use original logic (only checks instances)
            if node_states and all(n.get("state") in terminal_success for n in node_states):
                return SessionStatus.COMPLETED

        # 5. ended_at is set but not all nodes succeeded → FAILED
        if self.ended_at:
            return SessionStatus.FAILED

        # 6. Staleness detection — no active nodes and last_updated_at is stale
        if self.last_updated_at:
            elapsed = (datetime.now() - self.last_updated_at).total_seconds()
            if elapsed > STALENESS_THRESHOLD_SECONDS:
                return SessionStatus.STALLED

        # 7. Can still progress
        return SessionStatus.RUNNING

    def _get_node_instance_values(self) -> list[dict]:
        """Get node instance values."""
        return list(self.node_instances.values())

    # Helper methods for node instances
    def get_node_instance(self, node_id: str) -> dict | None:
        """Get a node instance by ID."""
        return self.node_instances.get(node_id)

    def set_node_instance(self, node_id: str, instance_dict: dict) -> None:
        """Set a node instance."""
        self.node_instances[node_id] = instance_dict
        self.last_updated_at = datetime.now()

    def update_node_state(self, node_id: str, state: str) -> None:
        """Update a node's state."""
        if node_id not in self.node_instances:
            self.node_instances[node_id] = create_node_instance(node_id, state)
        else:
            self.node_instances[node_id]["state"] = state
            if state.endswith("_running"):
                self.node_instances[node_id]["started_at"] = datetime.now().isoformat()
            elif state.endswith(("_completed", "_failed", "_rejected", "_timeout")):
                self.node_instances[node_id]["ended_at"] = datetime.now().isoformat()
        self.last_updated_at = datetime.now()

    def create_or_update_node(
        self,
        node_id: str,
        state: str,
        model_name: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        """Create or update a node instance with complete NodeInstance fields.

        This method creates node instances with all fields including model_name
        and agent_name, enabling the UI to display which AI model is executing
        each workflow stage.

        Args:
            node_id: Unique identifier for the node
            state: Current state of the node
            model_name: Resolved model name (e.g., "anthropic/claude-opus-4-6")
            agent_name: Agent name (e.g., "planner", "implementer")
        """
        if node_id not in self.node_instances:
            self.node_instances[node_id] = create_node_instance(
                node_id,
                state,
                model_name=model_name,
                agent_name=agent_name,
            )
        else:
            self.node_instances[node_id]["state"] = state
            if model_name is not None:
                self.node_instances[node_id]["model_name"] = model_name
            if agent_name is not None:
                self.node_instances[node_id]["agent_name"] = agent_name
            if state.endswith("_running"):
                self.node_instances[node_id]["started_at"] = datetime.now().isoformat()
            elif state.endswith(("_completed", "_failed", "_rejected", "_timeout")):
                self.node_instances[node_id]["ended_at"] = datetime.now().isoformat()
        self.last_updated_at = datetime.now()

    def update_node_token_usage(
        self,
        node_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """Update token usage for a specific node.

        Args:
            node_id: Node ID to update
            input_tokens: Number of input tokens consumed
            output_tokens: Number of output tokens generated
            cost_usd: Cost in USD for this execution
        """
        if node_id not in self.node_instances:
            self.node_instances[node_id] = create_node_instance(
                node_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
            )
        else:
            instance = self.node_instances[node_id]
            instance["input_tokens"] = instance.get("input_tokens", 0) + input_tokens
            instance["output_tokens"] = instance.get("output_tokens", 0) + output_tokens
            instance["total_tokens"] = instance["input_tokens"] + instance["output_tokens"]
            instance["cost_usd"] = instance.get("cost_usd", 0.0) + cost_usd

        self.last_updated_at = datetime.now()

    def reschedule_node(self, completed_node_id: str, successor_node_ids: list[str]) -> None:
        """Complete a node and schedule its successors on the executor cursor.

        Clears the current node, removes it from the ready queue, and adds
        all successor nodes. No-op with a warning if there is no cursor.

        Args:
            completed_node_id: Node ID that has finished execution.
            successor_node_ids: Node IDs to add to the ready queue.
        """
        cursor = self.executor_cursor
        if cursor is None:
            logger.warning(
                "reschedule_node called but no executor cursor on session %s",
                self.id,
            )
            return
        cursor.current_node_id = None
        cursor.remove_from_ready_queue(completed_node_id)
        for next_node in successor_node_ids:
            cursor.add_to_ready_queue(next_node)

    # Helper methods for loop state
    def get_loop_state(self, loop_id: str) -> LoopState | None:
        """Get loop state by ID."""
        data = self.loop_state.get(loop_id)
        return LoopState.from_dict(data) if data else None

    def set_loop_state(self, loop_id: str, loop_state: LoopState) -> None:
        """Set loop state."""
        self.loop_state[loop_id] = loop_state.to_dict()
        self.last_updated_at = datetime.now()

    # Helper methods for frozen artifacts
    def freeze_artifact(self, path: str, sha256_hash: str) -> None:
        """Record a frozen artifact hash.

        Args:
            path: Artifact path (relative to project root)
            sha256_hash: SHA256 hash of the artifact content
        """
        self.frozen_artifacts[path] = sha256_hash
        self.last_updated_at = datetime.now()

    def get_frozen_hash(self, path: str) -> str | None:
        """Get the frozen hash for an artifact path.

        Args:
            path: Artifact path

        Returns:
            SHA256 hash or None if not frozen
        """
        return self.frozen_artifacts.get(path)

    def is_frozen(self, path: str) -> bool:
        """Check if an artifact path is frozen.

        Args:
            path: Artifact path

        Returns:
            True if the path is frozen
        """
        return path in self.frozen_artifacts

    # Helper methods for artifacts
    def add_artifact(self, artifact: dict) -> None:
        """Add an artifact to this session."""
        if artifact not in self.artifacts:
            self.artifacts.append(artifact)
            self.last_updated_at = datetime.now()

    def get_artifacts_by_task(self, task_id: str) -> list[dict]:
        """Get all artifacts produced by a task."""
        return [a for a in self.artifacts if a.get("task_id") == task_id]

    # Token usage aggregation methods
    def get_node_usage(self, node_id: str) -> dict[str, int | float]:
        """Get token usage for a specific node.

        Args:
            node_id: Node ID to get usage for

        Returns:
            Dict with usage statistics
        """
        if node_id not in self.node_instances:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }

        instance = self.node_instances[node_id]
        return {
            "input_tokens": instance.get("input_tokens", 0),
            "output_tokens": instance.get("output_tokens", 0),
            "total_tokens": instance.get("total_tokens", 0),
            "cost_usd": instance.get("cost_usd", 0.0),
        }

    def get_session_usage_totals(self) -> dict[str, int | float]:
        """Get aggregated token usage for the entire session.

        Returns:
            Dict with total usage statistics
        """
        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "node_count": len(self.node_instances),
        }

        for instance in self.node_instances.values():
            totals["input_tokens"] += instance.get("input_tokens", 0)
            totals["output_tokens"] += instance.get("output_tokens", 0)
            totals["total_tokens"] += instance.get("total_tokens", 0)
            totals["cost_usd"] += instance.get("cost_usd", 0.0)

        return totals

    def get_usage_breakdown_by_node(self) -> dict[str, dict[str, int | float]]:
        """Get token usage breakdown by node.

        Returns:
            Dict mapping node_id to usage statistics
        """
        breakdown = {}
        for node_id, instance in self.node_instances.items():
            breakdown[node_id] = {
                "input_tokens": instance.get("input_tokens", 0),
                "output_tokens": instance.get("output_tokens", 0),
                "total_tokens": instance.get("total_tokens", 0),
                "cost_usd": instance.get("cost_usd", 0.0),
                "state": instance.get("state", "unknown"),
                "agent_name": instance.get("agent_name"),
                "model_name": instance.get("model_name"),
            }
        return breakdown

    def get_usage_by_agent(self) -> dict[str, dict[str, int | float]]:
        """Get token usage aggregated by agent.

        Returns:
            Dict mapping agent_name to usage statistics
        """
        agent_usage = {}
        for instance in self.node_instances.values():
            agent_name = instance.get("agent_name", "unknown")
            if agent_name not in agent_usage:
                agent_usage[agent_name] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "node_count": 0,
                }

            agent_usage[agent_name]["input_tokens"] += instance.get("input_tokens", 0)
            agent_usage[agent_name]["output_tokens"] += instance.get("output_tokens", 0)
            agent_usage[agent_name]["total_tokens"] += instance.get("total_tokens", 0)
            agent_usage[agent_name]["cost_usd"] += instance.get("cost_usd", 0.0)
            agent_usage[agent_name]["node_count"] += 1

        return agent_usage

    def get_usage_by_model(self) -> dict[str, dict[str, int | float]]:
        """Get token usage aggregated by model.

        Returns:
            Dict mapping model_name to usage statistics
        """
        model_usage = {}
        for instance in self.node_instances.values():
            model_name = instance.get("model_name", "unknown")
            if model_name not in model_usage:
                model_usage[model_name] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "node_count": 0,
                }

            model_usage[model_name]["input_tokens"] += instance.get("input_tokens", 0)
            model_usage[model_name]["output_tokens"] += instance.get("output_tokens", 0)
            model_usage[model_name]["total_tokens"] += instance.get("total_tokens", 0)
            model_usage[model_name]["cost_usd"] += instance.get("cost_usd", 0.0)
            model_usage[model_name]["node_count"] += 1

        return model_usage

    # Checkpoint methods
    def save(self, session_dir: Path) -> None:
        """Save session to session.json atomically."""
        import os
        import tempfile

        session_file = session_dir / "session.json"

        session_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=session_dir,
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(self.model_dump_json(indent=2, exclude_none=True, exclude={"status"}))
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)

        # Atomic rename
        tmp_path.replace(session_file)

    @classmethod
    def load(cls, session_dir: Path) -> "WorkflowSession | None":
        """Load session from session.json."""
        import json

        session_file = session_dir / "session.json"
        if not session_file.exists():
            return None

        data = json.loads(session_file.read_text())
        return cls.model_validate(data)

    @classmethod
    def create(
        cls,
        feature_id: str,
        snapshot_hash: str,
        project_path: Path | None = None,
    ) -> "WorkflowSession":
        """Create a new workflow session with generated ID.

        Args:
            feature_id: Feature ID
            snapshot_hash: Hash of the workflow snapshot
            project_path: Optional project root for git baseline capture
        """
        import uuid

        session_id = f"sess-{uuid.uuid4().hex[:8]}"

        baseline_commit = None
        workspace_root = None

        if project_path:
            baseline_commit, workspace_root = cls._capture_git_baseline(project_path)

        return cls(
            id=session_id,
            feature_id=feature_id,
            snapshot_hash=snapshot_hash,
            created_at=datetime.now(),
            last_updated_at=datetime.now(),
            baseline_commit=baseline_commit,
            workspace_root=workspace_root,
        )

    @staticmethod
    def _capture_git_baseline(project_path: Path) -> tuple[str | None, str | None]:
        """Capture git HEAD commit and workspace root.

        Args:
            project_path: Project root directory

        Returns:
            Tuple of (baseline_commit, workspace_root)
        """
        import subprocess

        try:
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(project_path),
                timeout=5,
            )
            toplevel = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                cwd=str(project_path),
                timeout=5,
            )
            commit = head.stdout.strip() if head.returncode == 0 else None
            root = toplevel.stdout.strip() if toplevel.returncode == 0 else None
            return commit, root
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, None
