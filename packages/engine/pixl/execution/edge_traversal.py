"""DAG edge traversal, condition evaluation, and loop constraint logic.

Extracted from graph_executor.py — handles following outgoing edges based
on execution results, evaluating edge conditions, and managing loop
iteration tracking.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pixl.models.session import LoopState
from pixl.models.workflow import EdgeTrigger

if TYPE_CHECKING:
    from pixl.execution.graph_executor import GraphExecutor

logger = logging.getLogger(__name__)


def follow_edges(
    executor: GraphExecutor,
    from_node: str,
    result_state: str,
    failure_kind: str | None = None,
) -> list[str]:
    """Follow outgoing edges based on execution result.

    Args:
        executor: GraphExecutor instance
        from_node: Source node ID
        result_state: "success", "failed", "skipped", or "waiting"
        failure_kind: "transient" or "fatal" (if failed)

    Returns:
        List of target node IDs to add to ready queue
    """
    next_nodes = []
    edges = executor.snapshot.graph.get_successors(from_node)

    for edge in edges:
        should_traverse = False
        is_loop_edge = False

        # Check if this is a loop edge (O(1) lookup via pre-built index)
        loop_constraint = executor._loop_constraint_by_edge.get((from_node, edge.to))
        is_loop_edge = loop_constraint is not None

        # Determine if edge should be traversed
        if (
            edge.on == EdgeTrigger.ALWAYS
            or edge.on == EdgeTrigger.SUCCESS
            and result_state == "success"
            or edge.on == EdgeTrigger.FAILURE
            and result_state == "failed"
        ):
            should_traverse = True
        elif edge.on == EdgeTrigger.CONDITION and edge.condition:
            # Evaluate condition
            should_traverse = evaluate_condition(
                executor,
                edge.condition,
                result_state,
                failure_kind,
                from_node,
            )

        # Check loop constraint if traversing a loop edge
        if is_loop_edge and should_traverse:
            if not can_enter_loop(executor, loop_constraint):
                should_traverse = False
            else:
                record_loop_iteration(executor, loop_constraint, from_node, edge.to)

        if should_traverse:
            next_nodes.append(edge.to)

    return next_nodes


def evaluate_condition(
    executor: GraphExecutor,
    condition: str,
    result_state: str,
    failure_kind: str | None,
    node_id: str,
) -> bool:
    """Evaluate an edge condition.

    Args:
        executor: GraphExecutor instance
        condition: PixlExpr condition string
        result_state: Current result state
        failure_kind: Failure kind if failed
        node_id: Current node ID

    Returns:
        True if condition evaluates to True
    """
    instance = executor.session.get_node_instance(node_id)
    context: dict[str, Any] = {
        "result_state": result_state,
        "failure_kind": failure_kind,
        "attempt": instance.get("attempt", 0) if instance else 0,
        "artifacts": [a.get("name", "") for a in executor.session.artifacts],
    }
    # Inject structured output payload for payload() expressions
    structured = executor.session.structured_outputs.get(node_id)
    if structured:
        context["payload"] = structured.get("payload", {})

    # Use the cached evaluator
    if executor._expr_evaluator is None:
        from pixl.execution.expression_evaluator import PixlExprEvaluator

        executor._expr_evaluator = PixlExprEvaluator(executor.artifacts_dir)
    try:
        return executor._expr_evaluator.evaluate(condition, context)
    except ValueError:
        return False


def can_enter_loop(executor: GraphExecutor, loop_constraint) -> bool:
    """Check if loop can be entered.

    Args:
        executor: GraphExecutor instance
        loop_constraint: LoopConstraint to check

    Returns:
        True if loop can be entered
    """
    loop_state = executor.session.get_loop_state(loop_constraint.id)
    if not loop_state:
        return True  # First iteration
    return loop_state.can_enter()


def record_loop_iteration(
    executor: GraphExecutor,
    loop_constraint,
    from_node: str,
    to_node: str,
) -> None:
    """Record entering a loop iteration.

    Args:
        executor: GraphExecutor instance
        loop_constraint: LoopConstraint being traversed
        from_node: Source node
        to_node: Target node
    """
    from pixl.models.event import Event

    loop_state = executor.session.get_loop_state(loop_constraint.id)
    if not loop_state:
        loop_data = LoopState(
            current_iteration=0,
            max_iterations=loop_constraint.max_iterations,
        )
    else:
        # loop_state is already a LoopState object from get_loop_state
        loop_data = loop_state

    loop_data.record_iteration(from_node, to_node, loop_constraint.edge_trigger.value)

    # Check max iterations
    if not loop_data.can_enter():
        skip_gates = executor.snapshot.workflow_config.get("metadata", {}).get(
            "skip_human_gate", False
        )

        if skip_gates:
            # Autonomous mode: continue with warning
            message = (
                f"Loop {loop_constraint.id} exhausted after "
                f"{loop_constraint.max_iterations} iterations. "
                f"Proceeding with caution."
            )
            executor._emit_event(
                Event.loop_exhaustion_warning(
                    session_id=executor.session.id,
                    loop_id=loop_constraint.id,
                    from_node=from_node,
                    max_iterations=loop_constraint.max_iterations,
                    message=message,
                )
            )
            if not hasattr(executor.session, "warnings"):
                object.__setattr__(executor.session, "warnings", [])
            executor.session.warnings.append(  # type: ignore[attr-defined]
                f"Review loop exhausted: {loop_constraint.max_iterations}"
                " iterations without approval"
            )
        else:
            # Human-in-the-loop: escalate by pausing workflow
            logger.warning(
                f"Loop {loop_constraint.id} exhausted after "
                f"{loop_constraint.max_iterations} iterations. "
                f"Workflow will pause for human review."
            )
            executor._emit_event(
                Event.session_paused(
                    session_id=executor.session.id,
                    reason=f"Loop {loop_constraint.id} exhausted - human approval required",
                )
            )

    executor.session.set_loop_state(loop_constraint.id, loop_data)
