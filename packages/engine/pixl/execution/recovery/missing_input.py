"""Missing-input backtracking recovery and artifact generation."""

from __future__ import annotations

import contextlib
import logging
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.errors import PixlError
from pixl.execution.node_state import (
    reset_instance_to_pending,
    workflow_max_attempts,
)
from pixl.execution.prompt_builder import resolve_template_string
from pixl.execution.recovery.helpers import (
    _build_step_result,
    pause_for_human,
)
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState
from pixl.models.workflow import NodeType

if TYPE_CHECKING:
    from pixl.execution.graph_executor import GraphExecutor

logger = logging.getLogger(__name__)


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


def write_missing_input_feedback(
    ex: GraphExecutor,
    *,
    node_id: str,
    missing_inputs: list[str],
    producer_nodes: list[str],
) -> Path:
    """Write deterministic missing-input diagnostics for recovery and human review."""
    ex.artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = ex.artifacts_dir / f"missing-inputs-{node_id}.md"
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
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
