"""Recovery and self-healing logic for workflow execution.

Extracted from graph_executor.py — handles error recovery policy evaluation,
contract repair, patch-and-test workflows, missing-input backtracking,
and human-pause escalation.
"""

from __future__ import annotations

import contextlib
import logging
import random
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.errors import (
    ContractError as PixlContractError,
)
from pixl.errors import (
    PixlError,
    ProviderError,
    StateError,
    StorageError,
)
from pixl.errors import (
    TimeoutError as PixlTimeoutError,
)
from pixl.execution.edge_traversal import follow_edges
from pixl.execution.node_state import (
    reset_instance_to_pending,
    update_node_instance_state,
    workflow_max_attempts,
)
from pixl.execution.prompt_builder import resolve_template_string
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState
from pixl.models.session import SessionStatus
from pixl.models.workflow import NodeType
from pixl.recovery.policy import RecoveryAction
from pixl.recovery.workflows.contract_repair import ContractRepairWorkflow
from pixl.recovery.workflows.patch_and_test import (
    PatchConstraints,
    PatchProposal,
)
from pixl.recovery.workflows.patch_and_test import (
    execute as patch_and_test_execute,
)

if TYPE_CHECKING:
    from pixl.recovery.engine import RecoveryDecision

    from .graph_executor import GraphExecutor

logger = logging.getLogger(__name__)

def _interruptible_sleep(session_id: str, seconds: float) -> None:
    """Sleep for *seconds* but wake early if the session's stop_event is set."""
    try:
        from pixl.execution.workflow_runner_manager import WorkflowRunnerManager

        stop_event = WorkflowRunnerManager.get_stop_event(session_id)
        if stop_event is not None:
            stop_event.wait(seconds)
            return
    except Exception:
        pass
    import time

    time.sleep(seconds)

def _maybe_finalize_terminal(ex: GraphExecutor, result: dict[str, Any]) -> None:
    """If result is terminal, emit completion event and mark session ended."""
    if not result.get("terminal"):
        return
    status = result["status"]
    terminal_event = (
        Event.session_completed(ex.session.id)
        if status == SessionStatus.COMPLETED
        else Event.session_failed(ex.session.id, "Workflow terminated")
    )
    terminal_committed = ex._commit_transition(
        event_type=terminal_event.type,
        node_id=None,
        payload=terminal_event.data,
        from_state=None,
        to_state=None,
    )
    result["events"].append(terminal_committed)
    ex._mark_session_ended()
    ex._save_session_summary()

def _build_step_result(
    ex: GraphExecutor,
    node_id: str,
    *,
    success: bool,
    events: list[Event],
    error: str | None = None,
    terminal: bool | None = None,
) -> dict[str, Any]:
    """Build a standardized step-level result dict for recovery paths."""
    status = ex._compute_status()
    is_terminal = terminal if terminal is not None else ex._is_terminal(status)
    result: dict[str, Any] = {
        "executed": True,
        "node_id": node_id,
        "success": success,
        "events": events,
        "status": status,
        "terminal": is_terminal,
    }
    if error is not None:
        result["error"] = error
    return result

def _extract_diff_from_output(text: str) -> str:
    """Extract a unified diff block from LLM output text."""
    import re

    match = re.search(r"```diff\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(---\s+.*?\n\+\+\+\s+.*?\n.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = text.split("\n")
    diff_lines = [
        ln for ln in lines if ln.startswith("+") or ln.startswith("-") or ln.startswith("@@")
    ]
    if len(diff_lines) >= 3:
        return "\n".join(diff_lines)
    return ""

def _extract_affected_files_from_diff(diff: str) -> list[str]:
    """Extract file paths from diff headers."""
    import re

    files = set()
    for match in re.finditer(r"^(?:---|\+\+\+)\s+([ab]/)?(.+)$", diff, re.MULTILINE):
        path = match.group(2).strip()
        if path and path != "/dev/null":
            files.add(path)
    return sorted(files)

# Error construction

def error_from_result(execution_result: dict[str, Any]) -> PixlError:
    """Build a typed PixlError from an execution_result dict.

    Used to feed the recovery policy when failures arrive as return
    values rather than exceptions.
    """
    error_msg = execution_result.get("error", "Unknown error")
    failure_kind = execution_result.get("failure_kind", "")
    error_type = execution_result.get("error_type", "")

    if error_type == "provider_error" or failure_kind == "provider":
        metadata = execution_result.get("error_metadata", {})
        return ProviderError(
            error_msg,
            http_status=metadata.get("http_status"),
            retry_after=metadata.get("retry_after"),
            provider=metadata.get("provider"),
            model=metadata.get("model"),
        )

    if error_type == "timeout_error" or failure_kind == "timeout":
        return PixlTimeoutError(error_msg)

    if error_type == "contract_error" or failure_kind == "contract_violation":
        metadata = execution_result.get("error_metadata", {})
        rule = metadata.get("rule") or failure_kind
        return PixlContractError(error_msg, rule=rule)

    if error_type == "state_error":
        return StateError(error_msg)

    return PixlError(
        error_type=error_type or "unknown",
        message=error_msg,
        is_transient=failure_kind == "transient",
    )

# Recovery orchestration functions

def handle_pixl_error(
    ex: GraphExecutor,
    error: PixlError,
    node_id: str | None,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Handle PixlError with recovery policy evaluation.

    Flow:
    1. Emit ERROR event (unchanged)
    2. Evaluate recovery policy via RecoveryEngine
    3. If RETRY + should_execute: reset node, sleep backoff, return non-terminal
    4. Else: proceed to TASK_FAILED (enriched with recovery info)
    """
    try:
        error_event = ex._emit_error_event(error, node_id=node_id)
    except StorageError:
        error_event = None
    if error_event:
        result["events"].append(error_event)

    result["executed"] = bool(node_id)
    result["node_id"] = node_id
    result["success"] = False
    result["error"] = error.message

    if node_id and not isinstance(error, StorageError):
        instance = ex.session.get_node_instance(node_id)
        attempt = instance.get("attempt", 0) if instance else 0

        try:
            decision = ex._recovery_engine.evaluate(
                error,
                node_id,
                attempt,
                max_attempts=workflow_max_attempts(ex.snapshot),
            )
        except Exception:
            logger.warning("Recovery engine evaluation failed for node %s", node_id, exc_info=True)
            decision = None

        if (
            decision is not None
            and decision.should_execute
            and decision.action == RecoveryAction.RETRY
        ):
            reset_node_for_retry(ex, node_id, decision)

            if decision.backoff_seconds > 0:
                actual_backoff = decision.backoff_seconds + random.uniform(0, decision.jitter_range)
                _interruptible_sleep(ex.session.id, actual_backoff)

            result["status"] = ex._compute_status()
            result["terminal"] = False
            return result

        failure_kind = "transient" if error.is_transient else "fatal"
        recovery_payload: dict[str, Any] = {
            "error": error.message,
            "failure_kind": failure_kind,
            "error_type": error.error_type,
            "error_metadata": error.metadata,
        }
        if decision is not None:
            recovery_payload["recovery_action"] = decision.action.value
            recovery_payload["recovery_reason"] = decision.reason

        cursor = ex.session.executor_cursor
        if cursor:
            if cursor.current_node_id == node_id:
                cursor.current_node_id = None
            cursor.remove_from_ready_queue(node_id)

        update_node_instance_state(
            ex.session,
            node_id,
            NodeState.TASK_FAILED,
            {
                "failure_kind": failure_kind,
                "error": error.message,
                "error_type": error.error_type,
            },
        )
        try:
            fail_event = ex._commit_transition(
                event_type=EventType.TASK_FAILED,
                node_id=node_id,
                payload=recovery_payload,
                from_state=None,
                to_state=NodeState.TASK_FAILED,
            )
            result["events"].append(fail_event)
        except PixlError:
            pass

    result["status"] = ex._compute_status()
    result["terminal"] = ex._is_terminal()

    if result["terminal"]:
        terminal_event = (
            Event.session_completed(ex.session.id)
            if result["status"] == SessionStatus.COMPLETED
            else Event.session_failed(ex.session.id, "Workflow terminated")
        )
        try:
            terminal_committed = ex._commit_transition(
                event_type=terminal_event.type,
                node_id=None,
                payload=terminal_event.data,
                from_state=None,
                to_state=None,
            )
            result["events"].append(terminal_committed)
        except PixlError:
            pass
        ex._mark_session_ended()
        ex._save_session_summary()

    return result

def reset_node_for_retry(
    ex: GraphExecutor,
    node_id: str,
    decision: RecoveryDecision,
) -> None:
    """Reset a failed node back to TASK_PENDING for retry."""
    # Preserve fields needed for retry context injection
    pre_reset_instance = ex.session.get_node_instance(node_id)
    saved_llm_session_id = (pre_reset_instance or {}).get("llm_session_id")
    saved_last_error = (pre_reset_instance or {}).get("error_message") or (
        pre_reset_instance or {}
    ).get("error")
    saved_provider_session_id = (pre_reset_instance or {}).get("provider_session_id")

    reset_instance_to_pending(ex.session, node_id, clear_error_fields=True)
    instance = ex.session.get_node_instance(node_id)
    if instance is None:
        return

    # Restore llm_session_id for conversation resumption on retry
    if saved_llm_session_id:
        instance["llm_session_id"] = saved_llm_session_id
    # Preserve error message for injection into retry prompt
    if saved_last_error:
        instance["last_error"] = saved_last_error
    # Preserve provider session ID for external provider resume (e.g. Gemini --resume)
    if saved_provider_session_id:
        instance["provider_session_id"] = saved_provider_session_id

    cursor = ex.session.executor_cursor
    if cursor:
        cursor.add_to_ready_queue(node_id)

    try:
        ex._commit_transition(
            event_type=EventType.TASK_RETRY_QUEUED,
            node_id=node_id,
            payload={"attempt": instance["attempt"]},
            from_state=NodeState.TASK_FAILED,
            to_state=NodeState.TASK_PENDING,
        )
    except PixlError:
        ex._persist_event(
            Event.task_retry_queued(
                ex.session.id,
                node_id,
                attempt=instance["attempt"],
            )
        )

def escalate_recovery(
    ex: GraphExecutor,
    node_id: str,
    reason: str,
    **extra_data: Any,
) -> None:
    """Record a recovery escalation event."""
    ex._recovery_counters["escalations"] += 1
    data: dict[str, Any] = {"reason": reason}
    if extra_data:
        data.update(extra_data)
    ex._persist_event(
        Event.create(
            EventType.RECOVERY_ESCALATED,
            ex.session.id,
            node_id=node_id,
            data=data,
        )
    )

def try_recovery_for_result(
    ex: GraphExecutor,
    node_id: str,
    execution_result: dict[str, Any],
    events: list[Event],
    persisted_events: list[Event],
) -> dict[str, Any] | None:
    """Evaluate recovery for a non-exception task failure.

    Returns a step-result dict if recovery triggers a retry (caller
    should return it immediately), or None to fall through to the
    normal TASK_FAILED commit path.
    """
    instance = ex.session.get_node_instance(node_id)
    attempt = instance.get("attempt", 0) if instance else 0
    failure_kind = execution_result.get("failure_kind", "")

    if failure_kind == "missing_inputs":
        return attempt_missing_input_recovery(
            ex,
            node_id=node_id,
            execution_result=execution_result,
            events=events,
            persisted_events=persisted_events,
            attempt=attempt,
        )

    if failure_kind == "validation_exhausted":
        reason = execution_result.get("error") or "Validation attempts exhausted"
        return pause_for_human(
            ex,
            node_id=node_id,
            reason=reason,
            execution_result=execution_result,
            events=events,
            persisted_events=persisted_events,
        )

    error = error_from_result(execution_result)

    ex._recovery_counters["requested"] += 1

    try:
        decision = ex._recovery_engine.evaluate(
            error,
            node_id,
            attempt,
            max_attempts=workflow_max_attempts(ex.snapshot),
        )
    except Exception:
        logger.warning("Recovery policy evaluation failed for node %s", node_id, exc_info=True)
        return None

    if decision.should_execute and decision.action == RecoveryAction.RETRY:
        ex._recovery_counters["retries"] += 1
        logger.info(
            "recovery.retry",
            extra={"node_id": node_id, "attempt": attempt, "backoff": decision.backoff_seconds},
        )
        reset_node_for_retry(ex, node_id, decision)

        if decision.backoff_seconds > 0:
            actual_backoff = decision.backoff_seconds + random.uniform(0, decision.jitter_range)
            _interruptible_sleep(ex.session.id, actual_backoff)

        return _build_step_result(
            ex,
            node_id,
            success=False,
            events=persisted_events + events,
            error=error.message,
            terminal=False,
        )

    if decision.should_execute and decision.action == RecoveryAction.CONTRACT_REPAIR:
        ex._recovery_counters["contract_repairs"] += 1
        repair_result = attempt_contract_repair(
            ex,
            node_id,
            execution_result,
            events,
            persisted_events,
            decision,
        )
        if repair_result is not None:
            ex._recovery_counters["successes"] += 1
            return repair_result

    if decision.should_execute and decision.action == RecoveryAction.PATCH_AND_TEST:
        ex._recovery_counters["patch_and_test"] += 1
        pt_result = attempt_patch_and_test(
            ex,
            node_id,
            execution_result,
            events,
            persisted_events,
            decision,
        )
        if pt_result is not None:
            ex._recovery_counters["successes"] += 1
            return pt_result

    execution_result.setdefault("final_event_payload", {})
    execution_result["final_event_payload"]["recovery_action"] = decision.action.value
    execution_result["final_event_payload"]["recovery_reason"] = decision.reason
    return None

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
        artifact_loader=ex._load_session_artifact_safe,
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
        diff = _extract_diff_from_output(llm_output)

    if not diff:
        escalate_recovery(ex, node_id, "Could not extract diff from LLM output")
        return None

    if not affected_files:
        affected_files = _extract_affected_files_from_diff(diff)

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
        cursor = ex.session.executor_cursor
        cursor.current_node_id = None
        cursor.remove_from_ready_queue(node_id)
        for next_node in next_nodes:
            cursor.add_to_ready_queue(next_node)

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

    cursor = ex.session.executor_cursor
    cursor.current_node_id = None
    cursor.remove_from_ready_queue(node_id)
    for next_node in next_nodes:
        cursor.add_to_ready_queue(next_node)

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

# Missing input recovery

def attempt_missing_input_recovery(
    ex: GraphExecutor,
    *,
    node_id: str,
    execution_result: dict[str, Any],
    events: list[Event],
    persisted_events: list[Event],
    attempt: int,
) -> dict[str, Any]:
    """Backtrack to producer stages when required inputs are missing."""
    missing_inputs = execution_result.get("missing_inputs") or []
    if not isinstance(missing_inputs, list):
        missing_inputs = []
    missing_inputs = [str(v) for v in missing_inputs if str(v).strip()]

    producer_nodes = infer_missing_input_producers(ex, node_id, missing_inputs)
    feedback_path = write_missing_input_feedback(
        ex,
        node_id=node_id,
        missing_inputs=missing_inputs,
        producer_nodes=producer_nodes,
    )

    max_attempts = workflow_max_attempts(ex.snapshot)
    if attempt >= max_attempts - 1:
        reason = f"Missing inputs after {max_attempts} attempts: " + (
            ", ".join(missing_inputs) if missing_inputs else "unknown inputs"
        )
        execution_result.setdefault("error_metadata", {})
        execution_result["error_metadata"]["feedback_artifact"] = str(feedback_path)
        return pause_for_human(
            ex,
            node_id=node_id,
            reason=reason,
            execution_result=execution_result,
            events=events,
            persisted_events=persisted_events,
        )

    if not producer_nodes:
        reason = "Unable to infer producer stages for missing inputs: " + (
            ", ".join(missing_inputs) if missing_inputs else "unknown inputs"
        )
        execution_result.setdefault("error_metadata", {})
        execution_result["error_metadata"]["feedback_artifact"] = str(feedback_path)
        return pause_for_human(
            ex,
            node_id=node_id,
            reason=reason,
            execution_result=execution_result,
            events=events,
            persisted_events=persisted_events,
        )

    nodes_to_reset: set[str] = {node_id}
    for producer in producer_nodes:
        nodes_to_reset.add(producer)
        nodes_to_reset.update(collect_path_nodes(ex, producer, node_id))
    reset_nodes_for_reexecution(ex, nodes_to_reset)

    current = ex.session.get_node_instance(node_id)
    if current is not None:
        current["attempt"] = current.get("attempt", 0) + 1
        current["failure_kind"] = None
        current["error_message"] = None
        current["blocked_reason"] = None
        current["started_at"] = None
        current["ended_at"] = None
        ex.session.update_node_state(node_id, NodeState.TASK_PENDING.value)

    cursor = ex.session.executor_cursor
    if cursor:
        cursor.current_node_id = None
        cursor.remove_from_ready_queue(node_id)
        for producer in producer_nodes:
            cursor.add_to_ready_queue(producer)

    try:
        retry_event = ex._commit_transition(
            event_type=EventType.TASK_RETRY_QUEUED,
            node_id=node_id,
            payload={
                "attempt": current.get("attempt", 0) if current else 0,
                "missing_inputs": missing_inputs,
                "producer_nodes": producer_nodes,
                "feedback_artifact": str(feedback_path),
            },
            from_state=NodeState.TASK_FAILED,
            to_state=NodeState.TASK_PENDING,
        )
    except PixlError:
        retry_event = Event.task_retry_queued(
            ex.session.id,
            node_id,
            attempt=current.get("attempt", 0) if current else 0,
        )
        ex._persist_event(retry_event)

    for event in events:
        with contextlib.suppress(PixlError):
            ex._emit_event(event)

    return _build_step_result(
        ex,
        node_id,
        success=False,
        events=persisted_events + events + [retry_event],
        error=execution_result.get("error", "Missing required inputs"),
        terminal=False,
    )

def infer_missing_input_producers(
    ex: GraphExecutor,
    node_id: str,
    missing_inputs: list[str],
) -> list[str]:
    """Infer likely producer stages for missing artifacts deterministically."""
    if not missing_inputs:
        return []

    variables = ex._build_contract_variables(node_id)
    target_inputs = {resolve_template_string(path, variables) for path in missing_inputs if path}
    producers: set[str] = set()

    for artifact in ex.session.artifacts:
        name = str(artifact.get("name", ""))
        if name in target_inputs:
            task_id = artifact.get("task_id")
            if isinstance(task_id, str) and task_id:
                producers.add(task_id)

    for stage_id, stage_cfg in ex._stage_configs.items():
        if stage_id == node_id:
            continue
        declared: set[str] = set()
        for path in stage_cfg.get("outputs", []) or []:
            declared.add(resolve_template_string(str(path), variables))

        contract_cfg = stage_cfg.get("contract") or {}
        if isinstance(contract_cfg, dict):
            for path in contract_cfg.get("must_write", []) or []:
                declared.add(resolve_template_string(str(path), variables))

        if declared.intersection(target_inputs):
            producers.add(stage_id)

    if not producers:
        queue = deque((pred, 1) for pred in ex.snapshot.graph.get_predecessors(node_id))
        visited: set[str] = set()
        ranked: list[tuple[int, str]] = []
        while queue:
            current, depth = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            ranked.append((depth, current))
            for pred in ex.snapshot.graph.get_predecessors(current):
                if pred not in visited:
                    queue.append((pred, depth + 1))
        ranked.sort(key=lambda item: (item[0], item[1]))
        producers = {stage_id for _, stage_id in ranked[:3]}

    return sorted(producers)

def collect_path_nodes(
    ex: GraphExecutor,
    source_id: str,
    target_id: str,
) -> set[str]:
    """Collect task nodes that lie on any forward path from source to target."""
    cache_key = (source_id, target_id)
    cached = ex._path_nodes_cache.get(cache_key)
    if cached is not None:
        return set(cached)

    collected: set[str] = set()

    def _dfs(current: str, path: list[str]) -> bool:
        if current in path:
            return False
        path.append(current)
        if current == target_id:
            collected.update(path)
            path.pop()
            return True

        found = False
        successors = sorted(
            (edge.to for edge in ex.snapshot.graph.get_successors(current)),
        )
        for nxt in successors:
            if _dfs(nxt, path):
                found = True
        path.pop()
        return found

    _dfs(source_id, [])
    ex._path_nodes_cache[cache_key] = set(collected)
    return collected

def reset_nodes_for_reexecution(ex: GraphExecutor, node_ids: set[str]) -> None:
    """Reset task nodes to TASK_PENDING for deterministic re-execution."""
    for nid in sorted(node_ids):
        node = ex.snapshot.graph.nodes.get(nid)
        if not node or node.type != NodeType.TASK:
            continue
        if not ex.session.get_node_instance(nid):
            continue
        reset_instance_to_pending(
            ex.session,
            nid,
            increment_attempt=False,
            clear_error_fields=True,
            clear_blocked_reason=True,
        )

# Human escalation

def pause_for_human(
    ex: GraphExecutor,
    *,
    node_id: str,
    reason: str,
    execution_result: dict[str, Any],
    events: list[Event],
    persisted_events: list[Event],
) -> dict[str, Any]:
    """Block the node and pause the session with actionable diagnostics."""
    blocker_artifact, raw_output_artifact = write_human_blocker_artifact(
        ex,
        node_id=node_id,
        reason=reason,
        execution_result=execution_result,
    )

    instance = ex.session.get_node_instance(node_id)
    if instance:
        instance["state"] = NodeState.TASK_BLOCKED.value
        instance["blocked_reason"] = reason
        instance["started_at"] = None
        instance["ended_at"] = None
        ex.session.update_node_state(node_id, NodeState.TASK_BLOCKED.value)

    cursor = ex.session.executor_cursor
    if cursor:
        cursor.current_node_id = None
        cursor.remove_from_ready_queue(node_id)

    ex.session.paused_at = datetime.now()
    ex.session.pause_reason = f"{node_id}: {reason}"

    for event in events:
        with contextlib.suppress(PixlError):
            ex._emit_event(event)

    payload: dict[str, Any] = {
        "reason": reason,
        "blocker_artifact": blocker_artifact,
    }
    if raw_output_artifact:
        payload["raw_output_artifact"] = raw_output_artifact

    try:
        blocked_event = ex._commit_transition(
            event_type=EventType.TASK_BLOCKED,
            node_id=node_id,
            payload=payload,
            from_state=NodeState.TASK_FAILED,
            to_state=NodeState.TASK_BLOCKED,
        )
    except PixlError:
        blocked_event = Event.task_blocked(ex.session.id, node_id, reason=reason)
        blocked_event.data["blocker_artifact"] = blocker_artifact
        if raw_output_artifact:
            blocked_event.data["raw_output_artifact"] = raw_output_artifact
        ex._persist_event(blocked_event)

    return _build_step_result(
        ex,
        node_id,
        success=False,
        events=persisted_events + events + [blocked_event],
        error=reason,
        terminal=False,
    )

# Diagnostic artifact writers

def write_missing_input_feedback(
    ex: GraphExecutor,
    *,
    node_id: str,
    missing_inputs: list[str],
    producer_nodes: list[str],
) -> Path:
    """Write deterministic missing-input diagnostics for recovery and human review."""
    artifact_name = f"missing-inputs-{node_id}.md"
    path = ex.artifacts_dir / artifact_name
    lines = [
        f"# Missing Input Diagnostics: {node_id}",
        "",
        "## Missing Inputs",
    ]
    if missing_inputs:
        for item in missing_inputs:
            lines.append(f"- `{item}`")
    else:
        lines.append("- (none listed)")
    lines.extend(["", "## Candidate Producer Stages"])
    if producer_nodes:
        for stage_id in producer_nodes:
            lines.append(f"- `{stage_id}`")
    else:
        lines.append("- No producer inferred")
    lines.extend(
        [
            "",
            "This file was generated by GraphExecutor deterministic input validation.",
        ]
    )
    ex.store.save_artifact(ex.session.id, artifact_name, "\n".join(lines))
    return path

def write_human_blocker_artifact(
    ex: GraphExecutor,
    *,
    node_id: str,
    reason: str,
    execution_result: dict[str, Any],
) -> tuple[str, str | None]:
    """Write actionable diagnostics for paused human intervention."""
    artifact_name = f"blocked-{node_id}.md"
    metadata = execution_result.get("error_metadata") or {}
    missing_inputs = execution_result.get("missing_inputs") or metadata.get("missing_inputs") or []
    if not isinstance(missing_inputs, list):
        missing_inputs = []

    lines = [
        f"# Stage Blocked: {node_id}",
        "",
        "## Action Summary",
        f"- Stage: `{node_id}`",
        f"- Primary issue: {reason}",
        f"- Resume command: `pixl resume {ex.session.id}`",
        "",
        "## Why Execution Paused",
        reason,
        "",
        "## Missing Inputs",
    ]
    if missing_inputs:
        for item in missing_inputs:
            lines.append(f"- `{item}`")
    else:
        lines.append("- (not specified)")

    lines.extend(
        [
            "",
            "## Validation Details",
            f"- failure_kind: `{execution_result.get('failure_kind', 'unknown')}`",
            f"- error_type: `{execution_result.get('error_type', 'unknown')}`",
            f"- attempts: `{metadata.get('attempts', 'n/a')}`"
            f" / `{metadata.get('max_attempts', workflow_max_attempts(ex.snapshot))}`",
            "",
            "## Next Actions",
            "1. Create or fix the missing artifacts/inputs.",
            "2. Review this stage's last output and violation list.",
            f"3. Resume with: `pixl resume {ex.session.id}`",
            "",
        ]
    )
    ex.store.save_artifact(ex.session.id, artifact_name, "\n".join(lines))

    raw_excerpt = execution_result.get("raw_output_excerpt")
    raw_artifact_name: str | None = None
    if isinstance(raw_excerpt, str) and raw_excerpt.strip():
        raw_artifact_name = f"blocked-{node_id}-raw-output.txt"
        ex.store.save_artifact(ex.session.id, raw_artifact_name, raw_excerpt)

    return artifact_name, raw_artifact_name
