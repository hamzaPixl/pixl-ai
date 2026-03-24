"""Core workflow execution.

The API routes import from ``pixl.execution.workflow_runner`` to launch
workflow sessions.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# How often to touch last_updated_at to prevent staleness detection.
# Must be well below STALENESS_THRESHOLD_SECONDS (60s).
_SESSION_TOUCH_INTERVAL_SECONDS = 30

# In-process execution tracking (observability only, not correctness)
#
# NOTE: workflow_background.py has a separate concurrency guard (set-based).
# This dict-based tracker is for the API entry point (run_workflow);
# workflow_background is used by the chain runner. They run in the same
# process but guard different entry points. WorkflowRunnerManager.start_session
# provides the authoritative thread-level guard.

_executor_lock = threading.Lock()
_executing_sessions: dict[str, tuple[str, str]] = {}  # session_id -> (project_id, owner_id)


@contextlib.contextmanager
def _heartbeat_during_step(session_store, session_id, interval=_SESSION_TOUCH_INTERVAL_SECONDS):
    """Keep last_updated_at fresh while executor.step() blocks."""
    stop = threading.Event()

    def _beat():
        while not stop.wait(interval):
            try:
                session_store.touch_session(session_id)
            except Exception:
                pass

    t = threading.Thread(target=_beat, daemon=True, name=f"heartbeat:{session_id[:12]}")
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=5)


def _mark_execution_active(session_id: str, owner_id: str, project_id: str = "") -> None:
    """Best-effort in-process marker (observability only, not correctness)."""
    with _executor_lock:
        _executing_sessions[session_id] = (project_id, owner_id)


def _release_execution(session_id: str, owner_id: str) -> None:
    """Clear in-process marker for *session_id* if owner matches."""
    with _executor_lock:
        current = _executing_sessions.get(session_id)
        if current and current[1] == owner_id:
            _executing_sessions.pop(session_id, None)


def get_active_sessions_for_project(project_id: str) -> list[str]:
    """Return in-process active sessions for the given project."""
    with _executor_lock:
        return [sid for sid, meta in _executing_sessions.items() if meta[0] == project_id]


# Core workflow execution


def run_workflow(
    project_path: Path,
    session_id: str,
    workflow_id: str,
    skip_approval: bool,
    db: Any,
    stop_event: threading.Event | None = None,
    *,
    run_id: str | None = None,
) -> None:
    """Run workflow execution in background.

    Uses in-process concurrency guard (one executor per session).
    Container lifecycle provides durable liveness detection.
    Heartbeat runs track each execution window as a first-class entity.
    """
    project_id = project_path.name if hasattr(project_path, "name") else ""
    owner_id = f"own-{uuid.uuid4().hex[:12]}"

    # Create heartbeat run if not provided (backward compat)
    if run_id is None:
        from pixl.models.heartbeat_run import HeartbeatRun

        run_id = HeartbeatRun.generate_id()
        invocation = (
            "start"
            if workflow_id not in ("resumed", "retry")
            else workflow_id.replace("resumed", "resume")
        )
        try:
            db.heartbeat_runs.create_run(run_id, session_id, invocation=invocation)
        except Exception:
            logger.warning("Failed to create heartbeat run for session %s", session_id)

    try:
        # Mark run as running
        try:
            db.heartbeat_runs.start_run(run_id)
            db.sessions.update_session(session_id, status="running", current_run_id=run_id)
        except Exception:
            logger.warning("Failed to start heartbeat run %s", run_id)

        _mark_execution_active(session_id, owner_id, project_id)
        _run_workflow_inner(
            project_path,
            session_id,
            workflow_id,
            skip_approval,
            db,
            stop_event,
            run_id=run_id,
        )
    finally:
        # Complete the heartbeat run
        try:
            row = db.sessions.get_session(session_id)
            computed_status = row.get("status", "") if row else ""
            run_status = "succeeded" if computed_status == "completed" else "failed"
            if computed_status in ("paused", "created"):
                run_status = "cancelled"
            db.heartbeat_runs.complete_run(run_id, status=run_status)
            if computed_status:
                db.sessions.update_session(session_id, status=computed_status)
        except Exception:
            logger.exception("Failed to complete heartbeat run %s", run_id)

        # Defensive: ensure ended_at is set if session isn't paused/created
        try:
            row = db.sessions.get_session(session_id)
            if row and not row.get("ended_at") and row.get("status") not in ("paused", "created"):
                db.sessions.update_session(session_id, ended_at=datetime.now().isoformat())
                logger.warning("Defensive ended_at for session %s on execution end", session_id)
        except Exception:
            logger.exception("Failed defensive ended_at for %s", session_id)

        _release_execution(session_id, owner_id)


def _auto_push_if_enabled(worktree_path: Path | None, feature_id: str) -> bool:
    """Push the feature branch if a worktree exists. Returns True if pushed."""
    with contextlib.suppress(Exception):
        if worktree_path and worktree_path.exists():
            from pixl.execution.git_utils import auto_push_feature_branch

            pushed, push_err = auto_push_feature_branch(worktree_path, feature_id=feature_id)
            if push_err:
                logger.warning("Auto-push skipped for %s: %s", feature_id, push_err)
            elif pushed:
                logger.info("Pushed feature branch pixl/%s to origin", feature_id)
                return True
    return False


def _run_workflow_inner(
    project_path: Path,
    session_id: str,
    workflow_id: str,
    skip_approval: bool,
    db: Any,
    stop_event: threading.Event | None = None,
    *,
    run_id: str | None = None,
) -> None:
    """Core workflow execution logic (called under concurrency guard)."""
    from pixl.execution.autonomy import (
        record_autonomy_outcome,
        resolve_latest_agent_task_pair,
        should_auto_approve_waiting_gate,
    )
    from pixl.execution.graph_executor import GraphExecutor
    from pixl.execution.workflow_helpers import (
        cleanup_feature_worktree,
        create_feature_worktree,
        create_state_bridge,
        ensure_pr_for_feature,
        get_waiting_gate_node,
        has_waiting_gates,
        set_worktree_baton_context,
    )
    from pixl.orchestration.core import OrchestratorCore
    from pixl.paths import get_sessions_dir
    from pixl.storage import SessionManager, WorkflowSessionStore

    logger.info("Starting workflow %s for session %s", workflow_id, session_id)

    # project_path = storage_dir; project_root may be a separate filesystem path.
    from pixl.projects.registry import get_project as _get_project

    _project_root = project_path  # default: use storage_dir
    project_id = project_path.name  # storage_dir basename IS the project_id
    _info = _get_project(project_id)
    if _info and _info.get("project_root"):
        _project_root = Path(_info["project_root"])

    try:
        session_store = WorkflowSessionStore(project_path)
        session = session_store.load_session(session_id)
        if not session:
            logger.error("Session %s not found", session_id)
            return

        snapshot = session_store.load_snapshot(session_id)
        if not snapshot:
            logger.error("Snapshot not found for session %s", session_id)
            return

        session_dir = get_sessions_dir(project_path) / session.id

        feature_id = session.feature_id or session_id
        try:
            worktree_path, branch_name = create_feature_worktree(_project_root, feature_id)
            session.workspace_root = str(worktree_path)
            session_store.save_session(session)
            # Set feature branch name (idempotent)
            with contextlib.suppress(Exception):
                db.backlog.update_feature(feature_id, branch_name=branch_name)
            # Populate baton with worktree context so agents know their branch
            with contextlib.suppress(Exception):
                set_worktree_baton_context(
                    db,
                    session_id,
                    branch_name=branch_name,
                    workspace_root=str(worktree_path),
                )
            orchestrator = OrchestratorCore(project_path)
        except Exception as e:
            if workflow_id == "resumed" and session.workspace_root:
                # Reuse existing workspace for resumed sessions
                logger.warning(
                    "Worktree creation failed for resumed session %s, reusing workspace: %s",
                    session_id,
                    e,
                )
                orchestrator = OrchestratorCore(project_path)
            else:
                logger.error("Failed to create worktree for session %s: %s", session_id, e)
                # Mark session as ended so it doesn't appear active / get retried
                try:
                    db.sessions.update_session(
                        session_id,
                        ended_at=datetime.now().isoformat(),
                    )
                except Exception:
                    logger.exception(
                        "Failed to mark session %s as ended after worktree error", session_id
                    )
                try:
                    db.events.emit(
                        event_type="error",
                        entity_type="session",
                        entity_id=session_id,
                        payload={"error": str(e), "phase": "worktree_creation"},
                    )
                except Exception:
                    logger.exception("Failed to emit error event for session %s", session_id)
                return

        session_manager = SessionManager(project_path)

        state_bridge = create_state_bridge(project_path)

        # Create a callback to wake WS streams on every event
        def _event_notify(event):
            try:
                from pixl_api.ws import notify_new_events

                notify_new_events()
            except ImportError:
                pass

        # Create executor — project_root must be storage_dir for DB/session persistence.
        executor = GraphExecutor(
            session,
            snapshot,
            session_dir,
            project_root=project_path,
            orchestrator=orchestrator,
            session_manager=session_manager,
            state_bridge=state_bridge,
            db=db,
            event_callback=_event_notify,
        )
        object.__setattr__(executor, "_current_run_id", run_id)  # For lock/budget/task-session tracking

        from pixl.execution.workflow_runner_manager import WorkflowRunnerManager

        WorkflowRunnerManager.register_orchestrator(session_id, orchestrator)

        from pixl.models.node_instance import NodeState

        for node_id, instance in session.node_instances.items():
            state = instance.get("state", "")
            if state == NodeState.TASK_RUNNING.value and instance.get("total_tokens", 0) == 0:
                logger.warning("Resetting zombie node %s from TASK_RUNNING to PENDING", node_id)
                instance["state"] = NodeState.TASK_PENDING.value
                cursor = session.executor_cursor
                if cursor and node_id not in cursor.ready_queue:
                    cursor.add_to_ready_queue(node_id)
        session_store.save_session(session)

        step_count = 0
        max_steps = 100
        last_heartbeat = time.monotonic()

        while step_count < max_steps:
            # Cooperative cancellation: exit promptly when stop is requested
            if stop_event is not None and stop_event.is_set():
                logger.info("Stop event set for session %s, exiting step loop", session_id)
                break

            # Heartbeat: refresh last_updated_at and heartbeat_at periodically
            now_mono = time.monotonic()
            if now_mono - last_heartbeat >= _SESSION_TOUCH_INTERVAL_SECONDS:
                session_store.touch_session(session_id)
                if run_id:
                    try:
                        db.heartbeat_runs.heartbeat(run_id)
                    except Exception:
                        pass
                last_heartbeat = now_mono

            # Check for external pause — lightweight DB check instead of full session reload.
            # Only reload from disk if paused_at is set (rare path).
            try:
                pause_row = db.sessions.get_session(session_id)
                if pause_row and pause_row.get("paused_at"):
                    session = session_store.load_session(session.id)
                    logger.info("Session %s paused externally", session_id)
                    break
            except Exception:
                pass  # DB check is best-effort; continue execution

            # Use the executor's in-memory session (updated via observer pattern)
            session = executor.session

            # Check for gates
            if has_waiting_gates(session):
                node_id = get_waiting_gate_node(session)
                if not node_id:
                    logger.warning("Detected waiting gate state but no gate node was found")
                    break
                agent_name, task_key = resolve_latest_agent_task_pair(session)
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
                        "Auto-approved gate %s (mode=%s level=%d reason=%s"
                        " confidence=%.3f threshold=%.3f samples=%d source=%s)",
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
                    # Pause at gate for human approval
                    logger.info(
                        "Workflow paused at gate %s (mode=%s level=%d reason=%s"
                        " confidence=%.3f threshold=%.3f samples=%d"
                        " min_samples=%d source=%s)",
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

            with _heartbeat_during_step(session_store, session_id):
                result = executor.step()

            if not result["executed"]:
                if result.get("terminal"):
                    break
                else:
                    logger.warning("No nodes ready to execute")
                    break

            step_count += 1

            # Budget enforcement: record cost and check limits
            if run_id:
                try:
                    node_id = result.get("node_id")
                    usage = result.get("usage", {})
                    from pixl.execution.budget import record_cost

                    budget_ok = record_cost(
                        db,
                        session_id,
                        run_id=run_id,
                        node_id=node_id,
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cost_usd=usage.get("cost_usd", 0.0),
                    )
                    if not budget_ok:
                        logger.info("Budget exceeded, pausing session %s", session_id)
                        break
                except Exception:
                    pass  # Budget check is best-effort

            # Use the executor's in-memory session (kept current by SessionManager observer)
            session = executor.session

            if has_waiting_gates(session):
                continue

        # Final status — set ended_at if session reached a terminal state
        session = executor.session
        from pixl.models.session import SessionStatus

        if session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
            db.sessions.update_session(
                session_id,
                ended_at=datetime.now().isoformat(),
            )
            record_autonomy_outcome(db, session)
            # Auto-push feature branch to preserve work
            wt = Path(session.workspace_root) if session.workspace_root else None
            pushed = _auto_push_if_enabled(wt, feature_id)

            if pushed and wt is not None:
                # Deterministic PR creation on successful completion
                if session.status == SessionStatus.COMPLETED:
                    with contextlib.suppress(Exception):
                        pr_info = ensure_pr_for_feature(
                            db=db,
                            feature_id=feature_id,
                            session_id=session_id,
                            worktree_path=wt,
                            storage_root=project_path,
                        )
                        if pr_info:
                            logger.info("PR created: %s", pr_info.url)
            # Only cleanup worktree when feature is done
            feat_row = db.backlog.get_feature(feature_id) if feature_id else None
            feat_status = str((feat_row or {}).get("status", ""))
            if feat_status == "done":
                cleanup_feature_worktree(_project_root, feature_id)

        logger.info(
            "Workflow %s completed with status %s after %d steps",
            workflow_id,
            session.status.value,
            step_count,
        )

    except Exception as e:
        logger.exception("Workflow execution failed: %s", e)
        # Set ended_at on crash so the session doesn't become a zombie
        try:
            db.sessions.update_session(
                session_id,
                ended_at=datetime.now().isoformat(),
            )
        except Exception:
            logger.exception("ZOMBIE SESSION %s: failed to set ended_at after crash", session_id)
        try:
            db.events.emit(
                event_type="error",
                entity_type="session",
                entity_id=session_id,
                payload={"error": str(e), "workflow_id": workflow_id},
            )
        except Exception:
            logger.exception("Failed to emit error event for session %s", session_id)
        # Auto-push on crash to preserve work
        wt_path = Path(session.workspace_root) if session.workspace_root else None  # type: ignore[reportPossiblyUnbound]
        _auto_push_if_enabled(wt_path, feature_id)  # type: ignore[reportPossiblyUnbound]
    finally:
        try:
            from pixl.execution.workflow_runner_manager import WorkflowRunnerManager

            WorkflowRunnerManager.unregister_orchestrator(session_id)
        except Exception:
            logger.exception("Failed to unregister orchestrator for session %s", session_id)
