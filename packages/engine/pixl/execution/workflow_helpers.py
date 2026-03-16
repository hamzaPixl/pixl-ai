"""Shared workflow helpers used by CLI and API execution paths.

These functions were duplicated across cli/workflow.py, cli/resume.py,
and api/routes/run.py. Centralized here for single-source-of-truth.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pixl.models.node_instance import NodeState

if TYPE_CHECKING:
    from pixl.git.pr_automation import PRInfo
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)

def create_feature_worktree(
    project_path: Path,
    feature_id: str,
    *,
    base_ref: str | None = None,
) -> tuple[Path, str]:
    """Create (or reuse) a feature-based git worktree.

    All sessions for the same feature share one branch and worktree,
    so work accumulates rather than being stranded per-session.

    Returns ``(worktree_path, branch_name)``.  Raises on failure.
    """
    from pixl.execution.git_utils import create_worktree_for_feature

    worktree_path, branch_name, error = create_worktree_for_feature(
        project_path,
        feature_id=feature_id,
        base_ref=base_ref,
    )
    if error or worktree_path is None:
        raise RuntimeError(f"Failed to create feature worktree: {error}")
    logger.info("Feature worktree ready: %s on branch %s", worktree_path, branch_name)
    return worktree_path, branch_name

def cleanup_feature_worktree(project_path: Path, feature_id: str) -> None:
    """Remove the worktree for a feature (keeps the branch)."""
    from pixl.execution.git_utils import cleanup_feature_worktree as _cleanup

    _cleanup(project_path, feature_id)

def create_state_bridge(project_path: Path, event_callback=None):
    """Create a WorkflowStateBridge for entity state transitions.

    Returns None if the state system is unavailable (no backlog, etc.).
    """
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

def has_waiting_gates(session) -> bool:
    """Check if session has gates waiting for approval."""
    for instance in session.node_instances.values():
        if instance.get("state") == NodeState.GATE_WAITING.value:
            return True
    return False

def get_waiting_gate_node(session) -> str | None:
    """Get the first waiting gate node ID."""
    for node_id, instance in session.node_instances.items():
        if instance.get("state") == NodeState.GATE_WAITING.value:
            return node_id
    return None

# Shared baton + PR helpers (used by CLI, API, and chain execution paths)

def set_worktree_baton_context(
    db: PixlDB,
    session_id: str,
    *,
    branch_name: str,
    base_ref: str | None = None,
    workspace_root: str,
) -> None:
    """Populate ``baton["worktree"]`` on a session row.

    Single-feature equivalent of ``chain/node_executor.build_worktree_context``.
    Agents read this context to know what branch they're on and where the
    worktree lives.
    """
    session_row = db.sessions.get_session(session_id)
    baton_raw = (session_row or {}).get("baton")
    baton = json.loads(baton_raw) if isinstance(baton_raw, str) else (baton_raw or {})
    if not isinstance(baton, dict):
        baton = {}
    baton["worktree"] = {
        "branch_name": branch_name,
        "base_ref": base_ref,
        "workspace_root": workspace_root,
    }
    db.sessions.update_session(session_id, baton=json.dumps(baton))

def ensure_pr_for_feature(
    *,
    db: PixlDB,
    feature_id: str,
    session_id: str,
    worktree_path: Path,
    storage_root: Path,
    base_branch: str = "main",
    base_remote: str = "origin",
    extra_trailers: str | None = None,
) -> PRInfo | None:
    """Deterministic PR creation for a single feature.

    Idempotent: discovers an existing PR before creating a new one.
    Updates feature metadata with ``pr_url`` on success.

    Returns ``PRInfo`` on success, ``None`` if nothing to push.
    """
    from pixl.git import pr_automation
    from pixl.storage import WorkflowSessionStore

    feature = db.backlog.get_feature(feature_id) or {}
    feature_title = str(feature.get("title") or feature_id)
    pr_title = f"feat: {feature_title}".strip()[:120]

    store = WorkflowSessionStore(storage_root, db=db)
    pr_body_text = store.load_artifact(session_id, "pr-body.md")

    # Commit any uncommitted changes
    if pr_automation.git_has_uncommitted_changes(worktree_path):
        body_parts = [f"Pixl-Feature: {feature_id}", f"Pixl-Session: {session_id}"]
        if extra_trailers:
            body_parts.append(extra_trailers)
        pr_automation.git_commit_all(
            worktree_path,
            subject=pr_title,
            body="\n".join(body_parts),
        )

    branch_name = pr_automation.git_current_branch(worktree_path)
    pr_automation.git_push_branch(worktree_path, remote=base_remote, branch_name=branch_name)

    # Discover or create PR
    info = pr_automation.try_get_pr_info(worktree_path)
    if info is None:
        info = pr_automation.create_pr(
            worktree_path,
            base_branch=base_branch,
            title=pr_title,
            body_text=pr_body_text or "",
        )
        # Refresh to capture full PR fields
        info = pr_automation.try_get_pr_info(worktree_path) or info

    # Persist PR URL on feature metadata
    try:
        db.backlog.update_feature(feature_id, branch_name=branch_name, pr_url=info.url)
    except Exception:
        logger.debug(
            "Non-critical: feature metadata update failed for %s", feature_id, exc_info=True
        )

    return info
