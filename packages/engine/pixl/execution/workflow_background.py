"""Background workflow execution loop (shared by API + chain runner).

This module owns:
- Per-session concurrency guard (at most one executor per session).
- Gate auto-approval logic (autonomy ladder).
- Autonomy outcome persistence at session terminal state.

It is intentionally free of FastAPI imports so it can be used from
execution services (e.g., chain_runner) without import cycles.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pixl.execution.autonomy import (  # noqa: F401
    record_autonomy_outcome,
    should_auto_approve_waiting_gate,
)
from pixl.execution.autonomy import (
    resolve_latest_agent_task_pair as _resolve_latest_agent_task_pair,
)
from pixl.storage.db.connection import PixlDB

_SESSION_TOUCH_INTERVAL_SECONDS = 30

logger = logging.getLogger(__name__)

# Concurrency guard — at most one executor per session

_executor_lock = threading.Lock()
_executing_sessions: set[str] = set()


def _try_start_execution(session_id: str) -> bool:
    """Atomically claim execution for *session_id*. Returns False if already running."""
    with _executor_lock:
        if session_id in _executing_sessions:
            return False
        _executing_sessions.add(session_id)
        return True


def _release_execution(session_id: str) -> None:
    """Release execution claim for *session_id*."""
    with _executor_lock:
        _executing_sessions.discard(session_id)


# Autonomy — delegated to pixl.execution.autonomy


def _create_state_bridge(project_path: Path, event_callback=None):
    try:
        from pixl.state.workflow_bridge import WorkflowStateBridge
        from pixl.storage.backlog_adapter import BacklogStoreAdapter

        adapter = BacklogStoreAdapter(project_path)
        if not adapter.exists():
            return None

        engine = adapter.engine
        return WorkflowStateBridge(engine, event_callback=event_callback)
    except Exception:
        return None


def _has_waiting_gates(session: Any) -> bool:
    from pixl.models.node_instance import NodeState

    for instance in session.node_instances.values():
        if instance.get("state") == NodeState.GATE_WAITING.value:
            return True
    return False


def _get_waiting_gate_node(session: Any) -> str | None:
    from pixl.models.node_instance import NodeState

    for node_id, instance in session.node_instances.items():
        if instance.get("state") == NodeState.GATE_WAITING.value:
            return node_id
    return None


def run_workflow_background(
    *,
    project_path: Path,
    session_id: str,
    workflow_id: str,
    skip_approval: bool,
    db: PixlDB,
    stop_event: threading.Event | None = None,
) -> None:
    """Run workflow execution for a session under a concurrency guard."""
    if not _try_start_execution(session_id):
        logger.info("Session %s already executing, skipping", session_id)
        return

    try:
        _run_workflow_inner(
            project_path=project_path,
            session_id=session_id,
            workflow_id=workflow_id,
            skip_approval=skip_approval,
            db=db,
            stop_event=stop_event,
        )
    finally:
        _release_execution(session_id)


def _run_workflow_inner(
    *,
    project_path: Path,
    session_id: str,
    workflow_id: str,
    skip_approval: bool,
    db: PixlDB,
    stop_event: threading.Event | None = None,
) -> None:
    from pixl.execution.graph_executor import GraphExecutor
    from pixl.orchestration.core import OrchestratorCore
    from pixl.paths import get_sessions_dir
    from pixl.storage import SessionManager, WorkflowSessionStore

    logger.info("Starting workflow %s for session %s", workflow_id, session_id)

    session_store = WorkflowSessionStore(project_path)
    session = session_store.load_session(session_id)
    if not session:
        logger.error("Session %s not found", session_id)
        return

    # If a session has a workspace_root, run the executor in that repo context
    # (git operations, code execution).  Session/snapshot reads always stay
    # anchored to ``project_path`` (the storage root) so worktrees — which
    # don't contain ``.pixl/`` — never shadow canonical storage.
    exec_root = project_path
    if session.workspace_root:
        with contextlib.suppress(Exception):
            exec_root = Path(session.workspace_root)

    # NOTE: session_store is NOT rebound to exec_root — sessions and snapshots
    # must always be read from the storage root (project_path).

    snapshot = session_store.load_snapshot(session_id)
    if not snapshot:
        logger.error("Snapshot not found for session %s", session_id)
        return

    session_dir = get_sessions_dir(project_path) / session.id

    orchestrator = OrchestratorCore(exec_root)
    session_manager = SessionManager(exec_root)
    # Use project_path (not exec_root) for state_bridge so entity transitions
    # work correctly when running in a git worktree. Worktrees don't have a
    # .pixl/ directory, so BacklogStoreAdapter.exists() would return False.
    state_bridge = _create_state_bridge(project_path)

    executor = GraphExecutor(
        session,
        snapshot,
        session_dir,
        project_root=exec_root,
        orchestrator=orchestrator,
        session_manager=session_manager,
        state_bridge=state_bridge,
    )

    from pixl.execution.workflow_runner_manager import WorkflowRunnerManager

    WorkflowRunnerManager.register_orchestrator(session_id, orchestrator)

    step_count = 0
    max_steps = 100
    last_heartbeat = time.monotonic()

    try:
        while step_count < max_steps:
            # Cooperative cancellation: exit promptly when stop is requested
            if stop_event is not None and stop_event.is_set():
                logger.info("Stop event set for session %s, exiting step loop", session_id)
                break

            now_mono = time.monotonic()
            if now_mono - last_heartbeat >= _SESSION_TOUCH_INTERVAL_SECONDS:
                session_store.touch_session(session_id)
                last_heartbeat = now_mono

            session = session_store.load_session(session.id)
            if session.paused_at:
                logger.info("Session %s paused externally", session_id)
                orchestrator.request_interrupt()
                break

            if _has_waiting_gates(session):
                node_id = _get_waiting_gate_node(session)
                if not node_id:
                    logger.warning("Detected waiting gate state but no gate node was found")
                    break
                agent_name, task_key = _resolve_latest_agent_task_pair(session)
                decision = should_auto_approve_waiting_gate(
                    db,
                    session_id=session.id,
                    feature_id=session.feature_id,
                    skip_approval=skip_approval,
                    agent_name=agent_name,
                    task_key=task_key,
                )

                if decision["approve"]:
                    session = session_manager.approve_gate(
                        session.id, node_id, approver="auto", snapshot=snapshot
                    )
                    logger.info(
                        "Auto-approved gate %s (mode=%s level=%d reason=%s "
                        "confidence=%.3f threshold=%.3f samples=%d source=%s)",
                        node_id,
                        decision.get("mode"),
                        int(decision.get("level", 0)),
                        decision.get("reason"),
                        float(decision.get("confidence", 0.0)),
                        float(decision.get("threshold", 0.0)),
                        int(decision.get("samples", 0)),
                        decision.get("confidence_source"),
                    )
                else:
                    logger.info(
                        "Workflow paused at gate %s (mode=%s level=%d reason=%s "
                        "confidence=%.3f threshold=%.3f samples=%d min_samples=%d source=%s)",
                        node_id,
                        decision.get("mode"),
                        int(decision.get("level", 0)),
                        decision.get("reason"),
                        float(decision.get("confidence", 0.0)),
                        float(decision.get("threshold", 0.0)),
                        int(decision.get("samples", 0)),
                        int(decision.get("min_samples", 0)),
                        decision.get("confidence_source"),
                    )
                    break

            # Use parallel step when multiple nodes are ready
            cursor = session.executor_cursor
            ready_count = len(cursor.ready_queue) if cursor and cursor.ready_queue else 0

            if ready_count > 1:
                import asyncio

                try:
                    result = asyncio.run(executor.step_parallel())
                except RuntimeError:
                    # Already inside an event loop — fall back to sequential
                    result = executor.step()
            else:
                result = executor.step()

            if not result["executed"]:
                if result.get("terminal"):
                    break
                logger.warning("No nodes ready to execute")
                break

            # For parallel steps, count all executed nodes
            parallel_node_ids = result.get("node_ids")
            if parallel_node_ids:
                step_count += len(parallel_node_ids)
            else:
                step_count += 1

            session = session_store.load_session(session.id)
            if _has_waiting_gates(session):
                continue

        session = session_store.load_session(session.id)
        from pixl.models.session import SessionStatus

        if session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
            db.sessions.update_session(
                session_id,
                ended_at=datetime.now().isoformat(),
            )
            record_autonomy_outcome(db, session)

        logger.info(
            "Workflow %s completed with status %s after %d steps",
            workflow_id,
            session.status.value,
            step_count,
        )
    except Exception as exc:
        logger.exception("Workflow execution failed: %s", exc)
        with contextlib.suppress(Exception):
            db.sessions.update_session(
                session_id,
                ended_at=datetime.now().isoformat(),
            )
        with contextlib.suppress(Exception):
            db.events.emit(
                event_type="error",
                entity_type="session",
                entity_id=session_id,
                payload={"error": str(exc), "workflow_id": workflow_id},
            )
    finally:
        WorkflowRunnerManager.unregister_orchestrator(session_id)
