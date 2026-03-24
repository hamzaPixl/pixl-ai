"""Contract repair recovery workflow orchestration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pixl.execution.edge_traversal import follow_edges
from pixl.execution.node_state import update_node_instance_state
from pixl.execution.prompt_builder import resolve_template_string
from pixl.execution.recovery.helpers import (
    _build_step_result,
    _maybe_finalize_terminal,
    escalate_recovery,
)
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState
from pixl.recovery.workflows.contract_repair import ContractRepairWorkflow

if TYPE_CHECKING:
    from pixl.execution.graph_executor import GraphExecutor
    from pixl.recovery.engine import RecoveryDecision

logger = logging.getLogger(__name__)


def attempt_contract_repair(
    ex: GraphExecutor,
    node_id: str,
    execution_result: dict[str, Any],
    events: list[Event],
    persisted_events: list[Event],
    decision: RecoveryDecision,
) -> dict[str, Any] | None:
    """Attempt contract repair via artifact-only re-query.

    Returns a complete step result on success, or None to fall through.
    """
    if not ex.orchestrator:
        escalate_recovery(ex, node_id, "No orchestrator available for repair")
        return None

    violations = execution_result.get("contract_violations") or [
        v.strip() for v in execution_result.get("error", "").split("; ") if v.strip()
    ]

    logger.info(
        "recovery.contract_repair.start",
        extra={"node_id": node_id, "violations": len(violations)},
    )

    repair_workflow = ContractRepairWorkflow(
        orchestrator=ex.orchestrator,
        project_root=ex.project_root,
        artifacts_dir=ex.artifacts_dir,
        session=ex.session,
        snapshot=ex.snapshot,
    )

    variables = ex._build_contract_variables(node_id)
    raw_stage_config = ex._get_stage_config(node_id)

    resolved_stage_config = dict(raw_stage_config)
    if "prompt" in resolved_stage_config:
        resolved_stage_config["prompt"] = resolve_template_string(
            resolved_stage_config["prompt"], variables
        )
    if "contract" in resolved_stage_config:
        resolved_stage_config["contract"] = ex._resolve_contract_data(
            resolved_stage_config["contract"], node_id
        )

    repair_result = repair_workflow.attempt_repair(
        node_id=node_id,
        violations=violations,
        max_attempts=decision.max_attempts,
        emit_event=ex._persist_event,
        resolved_stage_config=resolved_stage_config,
    )

    logger.info(
        "recovery.contract_repair.result",
        extra={
            "node_id": node_id,
            "success": repair_result.success,
            "attempt": repair_result.attempt,
        },
    )

    if repair_result.success:
        return finalize_repair_success(ex, node_id, repair_result, events, persisted_events)

    escalate_recovery(
        ex,
        node_id,
        "Contract repair exhausted",
        attempts=repair_result.attempt + 1,
        remaining_violations=repair_result.violations_after,
    )
    return None


def finalize_repair_success(
    ex: GraphExecutor,
    node_id: str,
    repair_result: Any,
    events: list[Event],
    persisted_events: list[Event],
) -> dict[str, Any]:
    """Build a complete step result for a successful contract repair."""
    update_node_instance_state(
        ex.session,
        node_id,
        NodeState.TASK_COMPLETED,
        {
            "repaired": True,
            "repair_attempt": repair_result.attempt,
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
                "repair_attempt": repair_result.attempt,
                "violations_fixed": repair_result.violations_before,
                "artifacts_modified": repair_result.artifacts_modified,
            },
        )
    )

    events.append(Event.contract_passed(ex.session.id, node_id))
    final_event = ex._commit_transition(
        event_type=EventType.TASK_COMPLETED,
        node_id=node_id,
        payload={"recovered": True, "repair_attempt": repair_result.attempt},
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
