"""Workflow models for the layered architecture.

This module defines the core workflow data structures:
- WorkflowTemplate: Versioned workflow definition
- WorkflowSnapshot: Immutable snapshot of a template at creation time
- ExecutionGraph: DAG with nodes, edges, and loop constraints
- Node: Graph nodes (task, gate, hook)
- Edge: Labeled edges with triggers (success, failure, always, condition)
"""

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, Field, field_serializer

class EdgeTrigger(StrEnum):
    """Edge traversal conditions."""

    SUCCESS = "success"
    FAILURE = "failure"
    ALWAYS = "always"
    CONDITION = "condition"

class TimeoutPolicy(StrEnum):
    """Gate timeout behavior."""

    REJECT = "reject"  # Timeout -> gate rejected (safe, default)
    CANCEL_SESSION = "cancel"  # Timeout -> cancel entire session
    AUTO_APPROVE = "auto"  # Timeout -> auto-approve (dangerous, opt-in)

class NodeType(StrEnum):
    """Types of nodes in the execution graph."""

    TASK = "task"
    GATE = "gate"
    HOOK = "hook"  # Deterministic Python function execution
    SUB_WORKFLOW = "sub_workflow"  # Nested workflow execution

class RetryPolicy(BaseModel):
    """Retry configuration for task nodes."""

    max_retries: int = Field(default=3, description="Maximum retry attempts")
    backoff_seconds: int = Field(default=5, description="Backoff between retries")
    retry_on: list[str] = Field(
        default_factory=list,
        description="Error patterns to match for retry",
    )

    def should_retry(self, attempt: int, error_message: str | None = None) -> bool:
        """Check if a task should be retried."""
        if attempt >= self.max_retries:
            return False
        if not self.retry_on:
            return True  # Retry on any error if no patterns specified
        if error_message:
            return any(pattern in error_message for pattern in self.retry_on)
        return True

class TaskConfig(BaseModel):
    """Configuration for task nodes."""

    agent: str = Field(default="default", description="Agent to execute this task")
    model: str | None = Field(
        default=None, description="Override model (uses agent default if None)"
    )
    retry_policy: RetryPolicy | None = Field(
        default_factory=RetryPolicy, description="Retry behavior"
    )
    timeout_seconds: int | None = Field(default=None, description="Task timeout (None = no limit)")
    max_turns: int = Field(default=50, description="Max SDK turns for this task")
    max_input_tokens: int | None = Field(
        default=None,
        description="Max input token budget for prompt. Context compiler will truncate to fit.",
    )

class GateConfig(BaseModel):
    """Configuration for gate nodes (human approval points)."""

    id: str = Field(description="Gate identifier (matches node.id)")
    name: str = Field(description="Human-readable gate name")
    description: str = Field(description="What requires approval")
    timeout_minutes: int | None = Field(
        default=None, description="Timeout in minutes (None = no timeout)"
    )
    timeout_policy: TimeoutPolicy = Field(
        default=TimeoutPolicy.REJECT, description="Behavior on timeout"
    )
    required_artifacts: list[str] = Field(
        default_factory=list,
        description="Artifact IDs that must exist before approval",
    )
    approvers: list[str] = Field(
        default_factory=list,
        description="Optional: who can approve (empty = anyone)",
    )
    freeze_artifacts: list[str] = Field(
        default_factory=list,
        description="Artifact paths to freeze (hash-lock) on gate approval",
    )

class HookConfig(BaseModel):
    """Configuration for hook nodes (deterministic Python functions)."""

    hook_id: str = Field(description="Registered hook function ID (e.g., 'init-git')")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters passed to the hook function"
    )

class Node(BaseModel):
    """A node in the execution graph.

    Represents a task, gate, or hook node.
    The actual runtime state is stored in NodeInstance.
    """

    id: str = Field(description="Unique node identifier")
    type: NodeType = Field(description="Node type")
    priority: int = Field(default=0, description="Execution priority (higher = first)")

    # Task-specific (if type == TASK)
    task_config: TaskConfig | None = Field(default=None, description="Task configuration")

    # Gate-specific (if type == GATE)
    gate_config: GateConfig | None = Field(default=None, description="Gate configuration")

    # Hook-specific (if type == HOOK)
    hook_config: HookConfig | None = Field(default=None, description="Hook configuration")

    # Metadata (arbitrary key-value pairs for extensibility)
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary metadata (e.g., sub_workflow ID for SUB_WORKFLOW nodes)",
    )

    # Graph properties (computed during graph construction)
    inbound_degree: int = Field(default=0, description="Number of incoming edges")
    outbound_degree: int = Field(default=0, description="Number of outgoing edges")

    @property
    def is_entry(self) -> bool:
        """Check if this is an entry node (no incoming edges)."""
        return self.inbound_degree == 0

    @property
    def is_exit(self) -> bool:
        """Check if this is an exit node (no outgoing edges)."""
        return self.outbound_degree == 0

    @property
    def is_task(self) -> bool:
        """Check if this is a task node."""
        return self.type == NodeType.TASK

    @property
    def is_gate(self) -> bool:
        """Check if this is a gate node."""
        return self.type == NodeType.GATE

    @property
    def is_hook(self) -> bool:
        """Check if this is a hook node."""
        return self.type == NodeType.HOOK

class Edge(BaseModel):
    """A labeled edge in the execution graph.

    Edges define traversal conditions between nodes.
    """

    to: str = Field(description="Target node ID")
    on: EdgeTrigger = Field(default=EdgeTrigger.SUCCESS, description="When to traverse this edge")
    condition: str | None = Field(
        default=None, description="PixlExpr condition (if on == CONDITION)"
    )

    def should_traverse(
        self,
        result_state: str,
        failure_kind: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if this edge should be traversed.

        Args:
            result_state: "success", "failed", "skipped"
            failure_kind: "transient" or "fatal" (if failed)
            context: Additional context for condition evaluation

        Returns:
            True if edge should be traversed
        """
        if self.on == EdgeTrigger.ALWAYS:
            return True
        if self.on == EdgeTrigger.SUCCESS:
            return result_state == "success"
        if self.on == EdgeTrigger.FAILURE:
            if result_state != "failed":
                return False
            # If no condition, always traverse on failure
            if not self.condition:
                return True
            # Condition would be evaluated by PixlExprEvaluator
            # For now, return True - actual evaluation happens in executor
            return True
        # Condition evaluated by PixlExprEvaluator
        # For now, defer to executor
        return self.on == EdgeTrigger.CONDITION

class LoopConstraint(BaseModel):
    """A loop constraint in the execution graph.

    Defines a back-edge that creates a loop, with iteration limits.
    """

    id: str = Field(description="Loop constraint identifier")
    from_node: str = Field(description="Source node ID (where loop exits)")
    to_node: str = Field(description="Target node ID (where loop re-enters)")
    max_iterations: int = Field(default=3, description="Maximum loop iterations")
    edge_trigger: EdgeTrigger = Field(
        default=EdgeTrigger.FAILURE,
        description="Which edge trigger activates this loop",
    )

class ExecutionGraph(BaseModel):
    """Directed graph with nodes, edges, and loop constraints.

    This is the structural definition of a workflow.
    Runtime state is tracked separately in NodeInstance.
    """

    nodes: dict[str, Node] = Field(default_factory=dict, description="All nodes in the graph")
    edges: dict[str, list[Edge]] = Field(
        default_factory=dict,
        description="Outgoing edges per node (node_id -> [edges])",
    )
    loop_constraints: list[LoopConstraint] = Field(
        default_factory=list, description="Loop constraints"
    )

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        if node.id not in self.edges:
            self.edges[node.id] = []

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        on: EdgeTrigger = EdgeTrigger.SUCCESS,
        condition: str | None = None,
    ) -> None:
        """Add an edge to the graph."""
        if from_node not in self.edges:
            self.edges[from_node] = []

        edge = Edge(to=to_node, on=on, condition=condition)
        self.edges[from_node].append(edge)

        # Invalidate predecessors cache
        if hasattr(self, "_predecessors_cache"):
            object.__delattr__(self, "_predecessors_cache")

        if from_node in self.nodes:
            self.nodes[from_node].outbound_degree += 1
        if to_node in self.nodes:
            self.nodes[to_node].inbound_degree += 1

    def add_loop_constraint(
        self,
        constraint_id: str,
        from_node: str,
        to_node: str,
        max_iterations: int = 3,
        edge_trigger: EdgeTrigger = EdgeTrigger.FAILURE,
    ) -> None:
        """Add a loop constraint."""
        constraint = LoopConstraint(
            id=constraint_id,
            from_node=from_node,
            to_node=to_node,
            max_iterations=max_iterations,
            edge_trigger=edge_trigger,
        )
        self.loop_constraints.append(constraint)

    @property
    def entry_nodes(self) -> list[str]:
        """Get nodes with no incoming edges."""
        return [nid for nid, node in self.nodes.items() if node.inbound_degree == 0]

    @property
    def exit_nodes(self) -> list[str]:
        """Get nodes with no outgoing edges."""
        return [nid for nid, node in self.nodes.items() if node.outbound_degree == 0]

    def get_successors(self, node_id: str) -> list[Edge]:
        """Get outgoing edges for a node."""
        return self.edges.get(node_id, [])

    def _build_predecessors_index(self) -> dict[str, list[str]]:
        """Build reverse edge index: node_id -> list of predecessor node_ids."""
        index: dict[str, list[str]] = {}
        for src, edge_list in self.edges.items():
            for edge in edge_list:
                index.setdefault(edge.to, []).append(src)
        return index

    def _build_normal_predecessors_index(self) -> dict[str, list[str]]:
        """Build reverse edge index excluding loop-back edges."""
        loop_edges = {(c.from_node, c.to_node) for c in self.loop_constraints}
        index: dict[str, list[str]] = {}
        for src, edge_list in self.edges.items():
            for edge in edge_list:
                if (src, edge.to) not in loop_edges:
                    index.setdefault(edge.to, []).append(src)
        return index

    def get_predecessors(self, node_id: str, *, exclude_loop_edges: bool = False) -> list[str]:
        """Get nodes that have edges to this node (O(1) via cached index).

        Args:
            node_id: The node to get predecessors for.
            exclude_loop_edges: If True, exclude loop-back edges from results.
                Use this for ready-queue computation to avoid deadlocks.
        """
        if exclude_loop_edges:
            if not hasattr(self, "_normal_predecessors_cache"):
                object.__setattr__(
                    self, "_normal_predecessors_cache", self._build_normal_predecessors_index()
                )
            cache: dict[str, list[str]] = self._normal_predecessors_cache  # type: ignore[attr-defined]
            return cache.get(node_id, [])
        if not hasattr(self, "_predecessors_cache"):
            object.__setattr__(self, "_predecessors_cache", self._build_predecessors_index())
        cache = self._predecessors_cache  # type: ignore[attr-defined]
        return cache.get(node_id, [])

    def get_loop_constraint_for_edge(self, from_node: str, to_node: str) -> LoopConstraint | None:
        """Get loop constraint if this edge is a loop back-edge."""
        for constraint in self.loop_constraints:
            if constraint.from_node == from_node and constraint.to_node == to_node:
                return constraint
        return None

    def validate_graph(self) -> list[str]:
        """Validate the graph structure.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check all edges reference valid nodes
        for src, edges in self.edges.items():
            if src not in self.nodes:
                errors.append(f"Edge source '{src}' not in nodes")
            for edge in edges:
                if edge.to not in self.nodes:
                    errors.append(f"Edge target '{edge.to}' (from '{src}') not in nodes")

        # Check all loop constraints reference valid nodes
        for constraint in self.loop_constraints:
            if constraint.from_node not in self.nodes:
                errors.append(
                    f"Loop constraint '{constraint.id}': from_node '{constraint.from_node}' not in nodes"
                )
            if constraint.to_node not in self.nodes:
                errors.append(
                    f"Loop constraint '{constraint.id}': to_node '{constraint.to_node}' not in nodes"
                )

        # Check for at least one entry node
        if not self.entry_nodes:
            errors.append("Graph has no entry nodes (all nodes have incoming edges)")

        # Check for at least one exit node
        if not self.exit_nodes:
            errors.append("Graph has no exit nodes (all nodes have outgoing edges)")

        # Check for disconnected nodes
        reachable = self._get_reachable_nodes()
        for node_id in self.nodes:
            if node_id not in reachable:
                errors.append(f"Node '{node_id}' is disconnected from entry nodes")

        return errors

    def _get_reachable_nodes(self) -> set[str]:
        """Get all nodes reachable from entry nodes."""
        reachable = set()
        to_visit = list(self.entry_nodes)

        while to_visit:
            node_id = to_visit.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)

            for edge in self.get_successors(node_id):
                if edge.to not in reachable:
                    to_visit.append(edge.to)

        return reachable

class WorkflowSnapshot(BaseModel):
    """Canonical snapshot of a workflow template.

    Snapshots are immutable - they capture the exact structure
    of a workflow at a specific version. Changes to templates
    create new snapshots.
    """

    snapshot_schema_version: int = Field(default=1, description="Schema version")
    template_id: str = Field(description="Template identifier (e.g., 'TDD-7')")
    template_version: str = Field(description="Template version (e.g., '1.3.0')")
    snapshot_hash: str = Field(description="SHA256 hash of snapshot content")
    created_at: datetime = Field(default_factory=datetime.now)

    # Graph definition
    graph: ExecutionGraph = Field(description="Execution graph structure")

    # Original workflow config (for prompts, variables, etc.)
    # Stored as dict to avoid circular import with WorkflowConfigYaml
    workflow_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Original workflow YAML configuration including prompts and variables",
    )

    # Metadata
    name: str = Field(description="Human-readable workflow name")
    description: str = Field(default="", description="Workflow description")
    tags: list[str] = Field(default_factory=list, description="Workflow tags")

    def compute_hash(self) -> str:
        """Compute hash of this snapshot for reproducibility."""
        # Exclude the hash field itself from computation
        content = self.model_dump_json(exclude={"snapshot_hash"}, exclude_none=True).encode()
        return sha256(content).hexdigest()

    def update_hash(self) -> "WorkflowSnapshot":
        """Update the snapshot_hash field based on current content."""
        self.snapshot_hash = self.compute_hash()
        return self

class WorkflowTemplate(BaseModel):
    """A versioned workflow template.

    Templates define reusable workflow structures that can be
    instantiated as sessions. Each template has a version history
    represented by snapshots.
    """

    id: str = Field(description="Template identifier (e.g., 'TDD-7')")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="", description="Template description")
    tags: list[str] = Field(default_factory=list, description="Template tags")

    # Latest snapshot
    current_snapshot: WorkflowSnapshot = Field(description="Latest snapshot of this template")

    # Version history
    version_history: dict[str, WorkflowSnapshot] = Field(
        default_factory=dict,
        description="All snapshots by version",
    )

    @field_serializer("version_history")
    def serialize_version_history(self, value: dict[str, WorkflowSnapshot]) -> dict[str, Any]:
        """Serialize version history for JSON output."""
        return {k: v.model_dump() for k, v in value.items()}

    def add_snapshot(self, snapshot: WorkflowSnapshot) -> None:
        """Add a snapshot to version history."""
        self.version_history[snapshot.template_version] = snapshot
        self.current_snapshot = snapshot

    def get_snapshot(self, version: str | None = None) -> WorkflowSnapshot | None:
        """Get a snapshot by version (or latest)."""
        if version is None:
            return self.current_snapshot
        return self.version_history.get(version)

    @classmethod
    def from_snapshot(cls, snapshot: WorkflowSnapshot) -> "WorkflowTemplate":
        """Create a template from a snapshot."""
        template = cls(
            id=snapshot.template_id,
            name=snapshot.name,
            description=snapshot.description,
            tags=snapshot.tags,
            current_snapshot=snapshot,
        )
        template.add_snapshot(snapshot)
        return template
