"""Patch-and-test recovery for code-level contract violations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pixl.execution.edge_traversal import follow_edges
from pixl.execution.node_state import update_node_instance_state
from pixl.execution.recovery.error_classifier import (
    extract_affected_files_from_diff,
    extract_diff_from_output,
)
from pixl.execution.recovery.helpers import (
    _build_step_result,
    _maybe_finalize_terminal,
    escalate_recovery,
)
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState
from pixl.recovery.workflows.patch_and_test import (
    PatchConstraints,
    PatchProposal,
)
from pixl.recovery.workflows.patch_and_test import (
    execute as patch_and_test_execute,
)

if TYPE_CHECKING:
    from pixl.execution.graph_executor import GraphExecutor
    from pixl.recovery.engine import RecoveryDecision

logger = logging.getLogger(__name__)


def attempt_patch_and_test(
    ex: GraphExecutor,
    node_id: str,
    execution_result: dict[str, Any],
    events: list[Event],
    persisted_events: list[Event],
    decision: RecoveryDecision,
) -> dict[str, Any] | None:
    """Attempt patch+test recovery for code-level contract violations.

    Returns a complete step result on success, or None on escalation/failure.
    """
    llm_output = execution_result.get("result_text", "")
    diff = execution_result.get("diff", "")
    affected_files = execution_result.get("affected_files", [])

    if not diff and not llm_output:
        escalate_recovery(ex, node_id, "No diff available for patch+test")
        return None

    if not diff:
        diff = extract_diff_from_output(llm_output)

    if not diff:
        escalate_recovery(ex, node_id, "Could not extract diff from LLM output")
        return None

    if not affected_files:
        affected_files = extract_affected_files_from_diff(diff)

    logger.info(
        "recovery.patch_and_test.start",
        extra={"node_id": node_id, "affected_files": len(affected_files)},
    )

    proposal = PatchProposal(
        diff=diff,
        affected_files=affected_files,
        description=f"Recovery patch for node {node_id}",
        confidence=0.5,
    )
    constraints = PatchConstraints()

    try:
        patch_result = patch_and_test_execute(
            proposal=proposal,
            constraints=constraints,
            project_root=ex.project_root,
            session_id=ex.session.id,
        )
    except Exception as exc:
        logger.warning(
            "recovery.patch_and_test.error",
            extra={"node_id": node_id, "error": str(exc)},
        )
        escalate_recovery(ex, node_id, f"Patch+test execution error: {exc}")
        return None

    logger.info(
        "recovery.patch_and_test.result",
        extra={
            "node_id": node_id,
            "applied": patch_result.applied,
            "escalated": patch_result.escalated,
        },
    )

    if patch_result.applied:
        update_node_instance_state(
            ex.session,
            node_id,
            NodeState.TASK_COMPLETED,
            {
                "patch_applied": True,
                "patch_reason": patch_result.reason,
            },
        )

        if ex.state_bridge and ex.session.feature_id:
            ex._trigger_entity_transition(node_id, True, None)

        ex._version_stage_outputs(node_id)

        next_nodes = follow_edges(ex, node_id, "success", None)
        ex.session.reschedule_node(node_id, next_nodes)

        ex._persist_event(
            Event.create(
                EventType.RECOVERY_SUCCEEDED,
                ex.session.id,
                node_id=node_id,
                data={
                    "recovery_type": "patch_and_test",
                    "affected_files": affected_files,
                    "reason": patch_result.reason,
                },
            )
        )

        events.append(Event.contract_passed(ex.session.id, node_id))
        final_event = ex._commit_transition(
            event_type=EventType.TASK_COMPLETED,
            node_id=node_id,
            payload={"recovered": True, "recovery_type": "patch_and_test"},
            from_state=NodeState.TASK_FAILED,
            to_state=NodeState.TASK_COMPLETED,
        )

        result = _build_step_result(
            ex,
            node_id,
            success=True,
            events=persisted_events + events + [final_event],
        )
        _maybe_finalize_terminal(ex, result)
        return result

    escalate_recovery(
        ex,
        node_id,
        f"Patch+test failed: {patch_result.reason}",
        violations=patch_result.violations,
        escalated=patch_result.escalated,
    )
    return None
