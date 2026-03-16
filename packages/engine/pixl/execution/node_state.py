"""Node instance state management for workflow execution.

Extracted from graph_executor.py — handles node instance lifecycle:
state transitions, metadata updates, agent/model resolution, and
retry budget computation.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pixl.models.node_instance import NodeState
from pixl.models.session import create_node_instance

if TYPE_CHECKING:
    from pixl.models.session import WorkflowSession
    from pixl.models.workflow import Node, WorkflowSnapshot


def update_node_instance_state(
    session: WorkflowSession,
    node_id: str,
    new_state: NodeState,
    execution_result: dict,
) -> None:
    """Update node instance state.

    Args:
        session: Workflow session
        node_id: Node ID
        new_state: New state
        execution_result: Execution result data
    """
    instance = session.get_node_instance(node_id)
    if not instance:
        instance = create_node_instance(node_id, new_state.value)

    instance["state"] = new_state.value

    if new_state == NodeState.TASK_RUNNING:
        instance["started_at"] = datetime.now().isoformat()
    elif NodeState.is_terminal(new_state):
        instance["ended_at"] = datetime.now().isoformat()

    if new_state == NodeState.TASK_FAILED:
        instance["failure_kind"] = execution_result.get("failure_kind", "transient")
        instance["error_message"] = execution_result.get("error")

    session.set_node_instance(node_id, instance)


def update_node_instance_metadata(
    session: WorkflowSession,
    node_id: str,
    agent_name: str | None = None,
    model_name: str | None = None,
    max_attempts: int | None = None,
    llm_session_id: str | None = None,
    provider_session_id: str | None = None,
) -> None:
    """Update node instance with agent and model metadata.

    Args:
        session: Workflow session
        node_id: Node ID
        agent_name: Agent name executing the node
        model_name: Model name being used
        max_attempts: Stage retry budget (includes initial attempt)
        llm_session_id: SDK conversation ID for in-thread follow-ups
        provider_session_id: External provider session ID for resume (e.g. Gemini CLI)
    """
    instance = session.get_node_instance(node_id)
    if not instance:
        instance = create_node_instance(node_id)

    if agent_name is not None:
        instance["agent_name"] = agent_name
    if model_name is not None:
        instance["model_name"] = model_name
    if max_attempts is not None:
        instance["max_attempts"] = max_attempts
    if llm_session_id:
        instance["llm_session_id"] = llm_session_id
    if provider_session_id:
        instance["provider_session_id"] = provider_session_id

    session.set_node_instance(node_id, instance)


def get_or_create_node_instance(session: WorkflowSession, node_id: str) -> dict:
    """Get or create a node instance.

    Args:
        session: Workflow session
        node_id: Node ID

    Returns:
        Node instance as dict
    """
    instance = session.get_node_instance(node_id)
    if instance:
        return instance
    return create_node_instance(node_id)


def reset_instance_to_pending(
    session: WorkflowSession,
    node_id: str,
    *,
    increment_attempt: bool = True,
    clear_error_fields: bool = False,
    clear_blocked_reason: bool = False,
    resume_session_id: str | None = None,
) -> None:
    """Reset a node instance to TASK_PENDING state.

    Consolidates the repeated reset pattern used by retry, revision,
    condition loops, and missing-input recovery.
    """
    instance = session.get_node_instance(node_id)
    if instance is None:
        return

    instance["state"] = NodeState.TASK_PENDING.value
    instance["started_at"] = None
    instance["ended_at"] = None
    if increment_attempt:
        instance["attempt"] = instance.get("attempt", 0) + 1
    if clear_error_fields:
        instance["failure_kind"] = None
        instance["error_message"] = None
    if clear_blocked_reason:
        instance["blocked_reason"] = None
    if resume_session_id:
        instance["resume_session_id"] = resume_session_id
    session.update_node_state(node_id, NodeState.TASK_PENDING.value)


def resolve_agent_and_model(
    node: Node,
    project_root: Path,
) -> tuple[str | None, str | None]:
    """Resolve agent name and effective model for a task node.

    Args:
        node: Node definition
        project_root: Project root for config resolution

    Returns:
        Tuple of (agent_name, effective_model)
    """
    if not node.task_config:
        return None, None

    task_config = node.task_config
    agent_name = task_config.agent
    effective_model = task_config.model or "claude-sonnet-4-6"

    return agent_name, effective_model


def workflow_max_attempts(snapshot: WorkflowSnapshot) -> int:
    """Resolve workflow-level stage attempt budget with safe fallback.

    If a ``confidence`` block is present in workflow config, uses its
    ``max_iterations`` as the safety valve instead of ``max_attempts``.
    """
    workflow_cfg = snapshot.workflow_config or {}

    # Confidence-based config takes precedence
    confidence_cfg = workflow_cfg.get("confidence")
    if isinstance(confidence_cfg, dict):
        raw_value = confidence_cfg.get("max_iterations", 10)
    else:
        raw_value = workflow_cfg.get("max_attempts", 3)

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return 3
    return max(1, min(value, 20))


def allow_simulated_execution() -> bool:
    """Whether task simulation is explicitly allowed for this process."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    raw = os.getenv("PIXL_ALLOW_SIMULATED_EXECUTION", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}
