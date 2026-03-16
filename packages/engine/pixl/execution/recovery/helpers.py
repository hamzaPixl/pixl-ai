"""Shared helpers for the recovery sub-package."""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.errors import PixlError
from pixl.execution.node_state import (
    workflow_max_attempts,
)
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState
from pixl.models.session import SessionStatus

if TYPE_CHECKING:
    from pixl.execution.graph_executor import GraphExecutor

logger = logging.getLogger(__name__)


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
    blocker_path = write_human_blocker_artifact(
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

    try:
        blocked_event = ex._commit_transition(
            event_type=EventType.TASK_BLOCKED,
            node_id=node_id,
            payload={
                "reason": reason,
                "blocker_artifact": str(blocker_path),
            },
            from_state=NodeState.TASK_FAILED,
            to_state=NodeState.TASK_BLOCKED,
        )
    except PixlError:
        blocked_event = Event.task_blocked(ex.session.id, node_id, reason=reason)
        ex._persist_event(blocked_event)

    for event in events:
        with contextlib.suppress(PixlError):
            ex._emit_event(event)

    return _build_step_result(
        ex,
        node_id,
        success=False,
        events=persisted_events + events + [blocked_event],
        error=reason,
        terminal=False,
    )


def write_human_blocker_artifact(
    ex: GraphExecutor,
    *,
    node_id: str,
    reason: str,
    execution_result: dict[str, Any],
) -> Path:
    """Write actionable diagnostics for paused human intervention."""
    ex.artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = ex.artifacts_dir / f"blocked-{node_id}.md"
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
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
