"""Main chain execution loop."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.execution.chain.config import load_chain_exec_config, patch_chain_exec_config
from pixl.execution.chain.conflict_detector import (
    emit_file_claims,
    extract_and_persist_signals,
    filter_conflicting_nodes,
    refresh_file_claims_from_session,
)
from pixl.execution.chain.consolidation import (
    record_chain_quality_scores,
    trigger_consolidation_workflow,
)
from pixl.execution.chain.judge import check_and_run_judge
from pixl.execution.chain.node_executor import (
    dispatch_node_pr_retry,
    dispatch_node_session,
    refine_node,
)
from pixl.execution.chain.paths import resolve_project_root
from pixl.execution.chain.pr_manager import ensure_pr_for_node
from pixl.execution.chain.topology import descendants, toposort_ready_nodes
from pixl.execution.chain_constants import CHAIN_TERMINAL_STATES
from pixl.execution.git_utils import auto_push_feature_branch, git_has_remote, refresh_base_ref
from pixl.execution.workflow_background import should_auto_merge_pr
from pixl.git import pr_automation
from pixl.storage.db.chain_plans import ChainPlanDB

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)


def run_chain_loop(
    *,
    db: PixlDB,
    chain_id: str,
    stop_event: threading.Event | None = None,
) -> None:
    """Scheduler loop: updates node status from session state and dispatches runnable nodes."""
    if stop_event is None:
        stop_event = threading.Event()

    store = ChainPlanDB(db)
    project_root = resolve_project_root(db)

    # Exec config rarely changes; reload only on status transitions.
    cfg = load_chain_exec_config(db, chain_id)
    _last_cfg_status: str | None = None  # track status to detect reload triggers

    def _unpack_cfg(cfg: dict[str, Any]) -> tuple[str, bool, str, str, str | None, bool, bool, str]:
        _workflow_id = str(cfg.get("workflow_id") or "tdd")
        _skip_approval = bool(cfg.get("skip_approval") or False)
        _base_remote = str(cfg.get("base_remote") or "origin")
        _base_branch = str(cfg.get("base_branch") or "")
        _base_ref = str(cfg.get("base_ref") or "") or None
        _pr_automation_enabled = bool(cfg.get("pr_automation", True))
        _pr_automation_available = _pr_automation_enabled and git_has_remote(
            project_root, _base_remote
        )
        _merge_method = str(cfg.get("merge_method") or "squash")
        return (
            _workflow_id,
            _skip_approval,
            _base_remote,
            _base_branch,
            _base_ref,
            _pr_automation_enabled,
            _pr_automation_available,
            _merge_method,
        )

    (
        workflow_id,
        skip_approval,
        base_remote,
        base_branch,
        base_ref,
        pr_automation_enabled,
        pr_automation_available,
        merge_method,
    ) = _unpack_cfg(cfg)

    # Edges are immutable during chain execution; fetch once.
    edges = store.get_edges(chain_id)

    # Adaptive sleep: start active, back off when idle, reset on activity.
    _active_sleep = 1.0
    _idle_step = 1.0
    _max_idle_sleep = 5.0
    idle_sleep = _active_sleep

    # Main loop: poll and schedule until chain leaves 'running'
    while not stop_event.is_set():
        chain = store.get_chain(chain_id)
        if chain is None:
            return

        status = str(chain.get("status", ""))

        # Reload exec config when the chain status changes (e.g. paused -> running).
        if status != _last_cfg_status:
            cfg = load_chain_exec_config(db, chain_id)
            (
                workflow_id,
                skip_approval,
                base_remote,
                base_branch,
                base_ref,
                pr_automation_enabled,
                pr_automation_available,
                merge_method,
            ) = _unpack_cfg(cfg)
            _last_cfg_status = status

        # Paused chains still reconcile node/session state, but do not dispatch new work.
        if status not in {"running", "paused"}:
            return

        nodes = store.get_execution_nodes(chain_id)

        # Track whether this iteration did meaningful work (for adaptive sleep).
        _activity_this_tick = False

        # 1) Reconcile running nodes based on their sessions' terminal status.
        running_nodes = [n for n in nodes if n.get("status") == "running" and n.get("session_id")]
        for node in running_nodes:
            session_id = node.get("session_id")
            session_row = db.sessions.get_session(str(session_id))
            if not session_row:
                continue
            session_status = str(session_row.get("status", ""))
            ended_at = session_row.get("ended_at")

            # Refresh file claims from running sessions so conflict detection stays current
            if not ended_at:
                refresh_file_claims_from_session(
                    db, chain_id, str(node.get("node_id", "")), str(session_id)
                )
                continue

            _activity_this_tick = True  # A running node reached a terminal state.
            node_id = str(node.get("node_id"))
            if session_status == "completed":
                # Stamp metadata so smart reset can detect session completion.
                try:
                    store.update_node_metadata(
                        chain_id,
                        node_id,
                        updates={"session_completed": True},
                    )
                except Exception:
                    logger.debug(
                        "Failed to update node metadata for %s:%s",
                        chain_id,
                        node_id,
                        exc_info=True,
                    )
                # Auto-push feature branch to preserve work
                try:
                    workspace_root_raw = str(session_row.get("workspace_root") or "")
                    if workspace_root_raw and Path(workspace_root_raw).exists():
                        feat_id = str(node.get("feature_id") or "")
                        if feat_id:
                            auto_push_feature_branch(Path(workspace_root_raw), feature_id=feat_id)
                except Exception:
                    logger.warning(
                        "Auto-push failed for node %s:%s",
                        chain_id,
                        node_id,
                        exc_info=True,
                    )
                # Post-session behavior is PR-driven: a node is only considered "completed"
                # once its PR is merged to the chain base branch.
                feature_id = str(node.get("feature_id") or "")
                if not feature_id:
                    store.mark_node_failed(chain_id, node_id, error="missing_feature_id")
                    continue

                if not pr_automation_available:
                    store.mark_node_completed(chain_id, node_id)
                    extract_and_persist_signals(db, chain_id, node_id, str(session_id))
                    continue

                if not base_branch:
                    store.set_node_error(chain_id, node_id, error="missing_base_branch")
                    if status == "running":
                        try:
                            store.pause_chain(chain_id)
                        except Exception:
                            logger.warning(
                                "Failed to pause chain %s",
                                chain_id,
                                exc_info=True,
                            )
                        status = "paused"
                    continue

                workspace_root = str(session_row.get("workspace_root") or "")
                worktree_path = Path(workspace_root) if workspace_root else project_root

                try:
                    pr_info = ensure_pr_for_node(
                        db=db,
                        chain_store=store,
                        chain_id=chain_id,
                        node_id=node_id,
                        feature_id=feature_id,
                        session_id=str(session_id),
                        worktree_path=worktree_path,
                        base_remote=base_remote,
                        base_branch=base_branch,
                    )
                except Exception as exc:
                    store.set_node_error(chain_id, node_id, error=f"pr_automation_failed:{exc}")
                    if status == "running":
                        try:
                            store.pause_chain(chain_id)
                        except Exception:
                            logger.warning(
                                "Failed to pause chain %s",
                                chain_id,
                                exc_info=True,
                            )
                        status = "paused"
                    continue

                hint = pr_automation.pr_merge_state_hint(pr_info)
                if hint == "merged":
                    store.mark_node_completed(chain_id, node_id)
                    extract_and_persist_signals(db, chain_id, node_id, str(session_id))
                    refreshed, err = refresh_base_ref(
                        project_root,
                        remote=base_remote,
                        base_branch=base_branch,
                    )
                    if refreshed and not err:
                        patch_chain_exec_config(db, chain_id, updates={"base_ref": refreshed})
                        base_ref = refreshed  # Keep local cache in sync.
                    continue

                if hint == "closed":
                    store.mark_node_failed(chain_id, node_id, error=f"pr_closed:{pr_info.url}")
                    continue

                meta = node.get("metadata") or {}
                decision = should_auto_merge_pr(
                    db,
                    session_id=str(session_id),
                    feature_id=feature_id,
                    skip_approval=skip_approval,
                )

                if decision.get("approve") and merge_method == "squash":
                    # If GitHub considers the PR blocked/dirty/behind, automation cannot proceed.
                    if hint.startswith("blocked:"):
                        store.set_node_error(chain_id, node_id, error=f"pr_merge_{hint}")
                        if status == "running":
                            try:
                                store.pause_chain(chain_id)
                            except Exception:
                                logger.warning(
                                    "Failed to pause chain %s",
                                    chain_id,
                                    exc_info=True,
                                )
                            status = "paused"
                        continue

                    if not bool(meta.get("auto_merge_requested")):
                        try:
                            pr_automation.request_squash_auto_merge(
                                worktree_path, pr_selector=pr_info.url
                            )
                            store.update_node_metadata(
                                chain_id,
                                node_id,
                                updates={
                                    "auto_merge_requested": True,
                                    "auto_merge_requested_at": datetime.now().isoformat(),
                                    "auto_merge_decision": decision,
                                },
                            )
                            try:
                                db.events.emit(
                                    event_type="chain_node_auto_merge_requested",
                                    entity_type="chain_node",
                                    entity_id=f"{chain_id}:{node_id}",
                                    payload={
                                        "chain_id": chain_id,
                                        "node_id": node_id,
                                        "pr_url": pr_info.url,
                                    },
                                )
                            except Exception:
                                logger.debug(
                                    "Failed to emit chain_node_auto_merge_requested event",
                                    exc_info=True,
                                )
                        except Exception as exc:
                            store.set_node_error(
                                chain_id, node_id, error=f"pr_merge_request_failed:{exc}"
                            )
                            if status == "running":
                                try:
                                    store.pause_chain(chain_id)
                                except Exception:
                                    logger.warning(
                                        "Failed to pause chain %s",
                                        chain_id,
                                        exc_info=True,
                                    )
                                status = "paused"
                    continue

                # Supervised trust: pause chain until a human merges the PR, then resume.
                store.set_node_error(chain_id, node_id, error="awaiting_pr_merge")
                store.update_node_metadata(
                    chain_id,
                    node_id,
                    updates={
                        "awaiting_pr_merge": True,
                        "auto_merge_decision": decision,
                    },
                )
                if status == "running":
                    try:
                        store.pause_chain(chain_id)
                    except Exception:
                        logger.warning(
                            "Failed to pause chain %s",
                            chain_id,
                            exc_info=True,
                        )
                    status = "paused"
                    try:
                        db.events.emit(
                            event_type="chain_execution_paused",
                            entity_type="chain",
                            entity_id=chain_id,
                            payload={
                                "reason": "awaiting_pr_merge",
                                "node_id": node_id,
                                "pr_url": pr_info.url,
                            },
                        )
                    except Exception:
                        logger.debug(
                            "Failed to emit chain_execution_paused event",
                            exc_info=True,
                        )
                continue
            if session_status == "failed":
                store.mark_node_failed(chain_id, node_id, error=str(session_row.get("error") or ""))
                continue
            # Defensive: an ended session should always be completed/failed.
            store.mark_node_failed(
                chain_id, node_id, error=f"unknown_session_status:{session_status}"
            )

        # Refresh nodes after reconciliation updates
        nodes = store.get_execution_nodes(chain_id)

        # 2) Block nodes whose predecessors are failed/blocked/cancelled
        runnable, newly_blocked = toposort_ready_nodes(nodes=nodes, edges=edges)
        if newly_blocked:
            _activity_this_tick = True
            store.mark_nodes_blocked(chain_id, newly_blocked, reason="blocked_by_dependency")
            nodes = store.get_execution_nodes(chain_id)
            runnable, _ = toposort_ready_nodes(nodes=nodes, edges=edges)

        # 3) Branch-aware failure propagation (block descendants of failed nodes)
        failed_nodes = [n for n in nodes if n.get("status") == "failed"]
        for failed in failed_nodes:
            failed_id = str(failed.get("node_id"))
            to_block = descendants(start_node_id=failed_id, edges=edges)
            store.mark_nodes_blocked(chain_id, to_block, reason=f"dependency_failed:{failed_id}")

        nodes = store.get_execution_nodes(chain_id)

        # 3b) stop_on_failure: once any node fails, cancel remaining pending work
        # and stop scheduling.
        if bool(chain.get("stop_on_failure")) and any(
            str(n.get("status")) == "failed" for n in nodes
        ):
            pending_ids = [
                str(n.get("node_id")) for n in nodes if str(n.get("status")) == "pending"
            ]
            store.mark_nodes_cancelled(chain_id, pending_ids, reason="stop_on_failure")
            nodes = store.get_execution_nodes(chain_id)
            runnable = []

        # 4) Terminal chain check
        terminal_states = CHAIN_TERMINAL_STATES
        if nodes and all(str(n.get("status")) in terminal_states for n in nodes):
            has_failures = any(
                str(n.get("status")) in {"failed", "blocked", "cancelled"} for n in nodes
            )
            final_status = "failed" if has_failures else "completed"
            store.set_chain_status(chain_id, final_status)
            record_chain_quality_scores(db, chain_id, nodes)
            try:
                store._db.events.emit(
                    event_type="chain_execution_completed"
                    if final_status == "completed"
                    else "chain_execution_failed",
                    entity_type="chain",
                    entity_id=chain_id,
                    payload={"status": final_status},
                )
            except Exception:
                logger.debug(
                    "Failed to emit chain terminal event for %s",
                    chain_id,
                    exc_info=True,
                )

            # Auto-trigger consolidation workflow if enabled and chain completed
            if final_status == "completed" and bool(cfg.get("consolidation_enabled")):
                try:
                    trigger_consolidation_workflow(db, chain_id, cfg)
                except Exception:
                    logger.debug(
                        "Consolidation trigger failed for chain %s", chain_id, exc_info=True
                    )
            return

        # 4.5) Post-wave judge review (always runs between wave transitions)
        if status == "running":
            judge_verdict = check_and_run_judge(
                db=db,
                store=store,
                chain_id=chain_id,
                nodes=nodes,
            )
            if judge_verdict == "block":
                store.pause_chain(chain_id)
                status = "paused"
                try:
                    db.events.emit(
                        event_type="chain_judge_blocked",
                        entity_type="chain",
                        entity_id=chain_id,
                        payload={"reason": "judge_blocked"},
                    )
                except Exception:
                    logger.debug(
                        "Failed to emit chain_judge_blocked event",
                        exc_info=True,
                    )
                idle_sleep = _active_sleep  # Reset on state change.
                stop_event.wait(timeout=_active_sleep)
                continue

        # 5) Dispatch runnable nodes respecting max_parallel (only when running)
        max_parallel = int(chain.get("max_parallel", 1) or 1)
        running_count = sum(1 for n in nodes if n.get("status") == "running")
        slots = max(0, max_parallel - running_count)
        if status == "running" and slots > 0 and runnable:
            _activity_this_tick = True
            # 5.1) Conflict detection: filter out nodes with file overlap
            dispatchable = filter_conflicting_nodes(db, chain_id, runnable[:slots])

            for node in dispatchable:
                node_meta = node.get("metadata") or {}

                # Refinement check: refine before dispatching if flagged.
                auto_refine_enabled = bool(cfg.get("auto_refine_enabled", False))
                max_refine_depth = int(cfg.get("max_refinement_depth", 2))
                refine_threshold = int(cfg.get("auto_refine_threshold", 8))
                node_depth = int(node_meta.get("decomposition_depth", 0))
                node_needs_refine = bool(node_meta.get("needs_refinement", False))
                node_estimate = int(node.get("estimate_points") or 0)
                should_refine = (
                    auto_refine_enabled
                    and node_depth < max_refine_depth
                    and (node_needs_refine or node_estimate >= refine_threshold)
                )
                if should_refine:
                    refine_node(db=db, store=store, chain_id=chain_id, node=node)
                    continue  # Sub-nodes will appear on next iteration.

                # PR retry: node has a completed session, skip workflow re-execution.
                if bool(node_meta.get("pr_retry")) and node.get("session_id"):
                    ok, pr_err = dispatch_node_pr_retry(
                        db=db,
                        chain_id=chain_id,
                        node=node,
                    )
                    if ok:
                        continue
                    # Fallback: clear session_id so full dispatch can proceed.
                    logger.warning(
                        "PR retry failed for node %s: %s — falling back to full dispatch",
                        node.get("node_id"),
                        pr_err,
                    )
                    with db.conn:
                        db.conn.execute(
                            "UPDATE execution_chain_nodes SET session_id = NULL "
                            "WHERE chain_id = ? AND node_id = ? AND status = 'pending'",
                            (chain_id, str(node.get("node_id") or "")),
                        )
                        db.conn.commit()

                node_workflow = str(node_meta.get("suggested_workflow") or "") or workflow_id
                session_id, error = dispatch_node_session(
                    db=db,
                    chain_id=chain_id,
                    node=node,
                    workflow_id=node_workflow,
                    skip_approval=skip_approval,
                    base_ref=base_ref,
                )
                if error:
                    if error == "node claim lost":
                        # Another runner claimed it; do not override node status.
                        continue
                    node_id = str(node.get("node_id") or "")
                    store.mark_node_failed(
                        chain_id,
                        node_id,
                        error=(f"{error} (session={session_id})" if session_id else error),
                    )
                else:
                    feat_id = str(node.get("feature_id") or "")
                    feat = db.backlog.get_feature(feat_id) if feat_id else None
                    emit_file_claims(db, chain_id, str(node.get("node_id") or ""), feat or {})

        # Adaptive sleep: short when active, back off when idle.
        if _activity_this_tick:
            idle_sleep = _active_sleep
        else:
            idle_sleep = min(idle_sleep + _idle_step, _max_idle_sleep)
        stop_event.wait(timeout=idle_sleep)
