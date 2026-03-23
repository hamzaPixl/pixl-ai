"""Gate rejection handling and revision path logic.

Extracted from graph_executor.py — handles gate rejection processing,
revision path resets, and condition-loop-triggered node resets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pixl.execution.edge_traversal import follow_edges
from pixl.execution.node_state import reset_instance_to_pending
from pixl.execution.prompt_builder import write_auto_review_feedback
from pixl.models.node_instance import NodeState
from pixl.models.workflow import EdgeTrigger

if TYPE_CHECKING:
    from pixl.execution.graph_executor import GraphExecutor


def process_gate_rejections(executor: GraphExecutor) -> None:
    """Process gate rejections that have revision loops.

    For each GATE_REJECTED node:
    1. Check for failure edges (revision loops)
    2. If exists: follow edges, reset nodes, write feedback, add targets to queue
    3. If not: leave as GATE_REJECTED (terminal)
    """
    rejected_gates = [
        (nid, inst)
        for nid, inst in executor.session.node_instances.items()
        if inst.get("state") == NodeState.GATE_REJECTED.value
    ]

    for gate_id, gate_instance in rejected_gates:
        # Check for failure edges from this gate
        next_nodes = follow_edges(executor, gate_id, "failed")

        if not next_nodes:
            continue  # No revision loop — gate rejection is terminal

        executor._write_rejection_feedback(gate_id)

        for target_id in next_nodes:
            reset_revision_path(executor, target_id, gate_id)

        gate_instance["state"] = NodeState.GATE_PENDING.value
        gate_instance["ended_at"] = None
        executor.session.update_node_state(gate_id, NodeState.GATE_PENDING.value)

        cursor = executor.session.executor_cursor
        if cursor:
            for target_id in next_nodes:
                cursor.add_to_ready_queue(target_id)


def collect_nodes_on_path(executor: GraphExecutor, source: str, target: str) -> set[str]:
    """DFS to collect all nodes on the path from source to target (exclusive).

    Returns the set of node IDs between source and target. The target
    node itself is NOT included; source IS included if it's on a valid path.

    Args:
        executor: GraphExecutor instance
        source: Starting node ID
        target: Ending node ID (excluded from result)

    Returns:
        Set of node IDs on the path
    """
    on_path: set[str] = set()
    visited: set[str] = set()

    def _dfs(node_id: str) -> bool:
        if node_id in visited:
            return False
        visited.add(node_id)
        if node_id == target:
            return True  # Reached target, don't include it
        on_path.add(node_id)
        for edge in executor.snapshot.graph.get_successors(node_id):
            if _dfs(edge.to):
                return True
        on_path.discard(node_id)  # Not on path to target
        return False

    _dfs(source)
    return on_path


def reset_revision_path(executor: GraphExecutor, target_id: str, gate_id: str) -> None:
    """Reset nodes on the path from target to gate for revision.

    Resets target node and all intermediate task nodes between
    target and gate to TASK_PENDING so they can re-execute.
    """
    to_reset = collect_nodes_on_path(executor, target_id, gate_id)

    for node_id in to_reset:
        reset_instance_to_pending(executor.session, node_id)


def process_condition_loop_resets(
    executor: GraphExecutor,
    from_node_id: str,
    next_nodes: list[str],
    *,
    defer_source_reset: bool = False,
) -> bool:
    """Handle node resets and feedback writing for condition-triggered loops.

    When a CONDITION loop edge fires (e.g., review → implement based on
    payload.recommendation), this method:
    1. Writes auto-review feedback from the review's structured output + artifacts
    2. Resets intermediate nodes between the loop target and the review node
    3. Resets the review node itself so it re-runs after revision
       (unless defer_source_reset=True, in which case the caller handles it)
    4. Propagates LLM session ID for conversation continuity

    Args:
        executor: GraphExecutor instance
        from_node_id: The node that just completed (e.g., review)
        next_nodes: Targets returned by _follow_edges
        defer_source_reset: If True, skip resetting the source node

    Returns:
        True if a condition loop was triggered and the source node reset
        was deferred (caller must reset it), False otherwise.
    """
    source_reset_deferred = False
    for constraint in executor._loop_constraints_by_from.get(from_node_id, ()):
        if constraint.edge_trigger == EdgeTrigger.CONDITION and constraint.to_node in next_nodes:
            # A condition loop was traversed — write feedback and reset nodes
            write_auto_review_feedback(
                from_node_id,
                session=executor.session,
                artifacts_dir=executor.artifacts_dir,
                store=executor.store,
            )

            source_instance = executor.session.get_node_instance(from_node_id)
            source_llm_session_id = None
            if source_instance:
                source_llm_session_id = source_instance.get("llm_session_id")

            to_reset = collect_nodes_on_path(executor, constraint.to_node, from_node_id)

            for node_id in to_reset:
                reset_instance_to_pending(
                    executor.session,
                    node_id,
                    resume_session_id=source_llm_session_id,
                )

            if defer_source_reset:
                source_reset_deferred = True
            else:
                reset_instance_to_pending(executor.session, from_node_id)

    return source_reset_deferred
