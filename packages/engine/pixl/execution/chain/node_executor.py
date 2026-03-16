"""Node session dispatch, worktree context, PR retry, and refinement."""

from __future__ import annotations

import contextlib
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.execution.chain.paths import resolve_project_root, resolve_storage_root
from pixl.execution.git_utils import (
    create_worktree_for_feature,
    ensure_git_available,
)
from pixl.execution.workflow_background import run_workflow_background
from pixl.paths import get_sessions_dir
from pixl.storage import WorkflowSessionStore, WorkflowStore
from pixl.storage.db.chain_plans import ChainPlanDB

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)

def build_worktree_context(
    db: PixlDB,
    chain_id: str,
    node_id: str,
    branch_name: str | None,
    base_ref: str | None,
    worktree_path: str | None,
) -> dict[str, Any]:
    """Build WorktreeContext fields for a dispatched node's baton.

    Queries chain nodes for parallel features and file claims from other nodes.
    """
    parallel_features: list[str] = []
    claimed_files: list[str] = []

    try:
        store = ChainPlanDB(db)
        nodes = store.get_execution_nodes(chain_id)

        current_node = next((n for n in nodes if str(n.get("node_id")) == node_id), None)
        current_wave = int((current_node or {}).get("wave", -1) or -1)

        for n in nodes:
            nid = str(n.get("node_id", ""))
            if nid == node_id:
                continue
            n_status = str(n.get("status", ""))
            n_wave = int(n.get("wave", -1) or -1)
            if n_wave == current_wave and n_status in {"pending", "running"}:
                feature_id = str(n.get("feature_id", ""))
                feature = db.backlog.get_feature(feature_id) if feature_id else None
                title = str((feature or {}).get("title", nid))
                parallel_features.append(title)

        file_claims = db.chain_signals.get_file_claims(chain_id)
        for filepath, claimant_nodes in file_claims.items():
            if node_id not in claimant_nodes:
                claimed_files.append(filepath)
    except Exception:
        logger.debug(
            "Non-critical: worktree context enrichment failed for node %s", node_id, exc_info=True
        )

    return {
        "branch_name": branch_name,
        "base_ref": base_ref,
        "workspace_root": worktree_path,
        "parallel_features": parallel_features[:20],
        "claimed_files": claimed_files[:50],
    }

def dispatch_node_session(
    *,
    db: PixlDB,
    chain_id: str,
    node: dict[str, Any],
    workflow_id: str,
    skip_approval: bool,
    base_ref: str | None,
) -> tuple[str | None, str | None]:
    """Create a session for a node and start background execution.

    Returns (session_id, error).
    """
    project_root = resolve_project_root(db)
    storage_root = resolve_storage_root(db)
    feature_id = str(node.get("feature_id") or "")
    node_id = str(node.get("node_id") or "")
    if not feature_id:
        return None, "node missing feature_id"
    if not node_id:
        return None, "node missing node_id"

    ok, err = ensure_git_available(project_root)
    if not ok:
        return None, err or "git unavailable"

    workflow_store = WorkflowStore(storage_root)
    try:
        template = workflow_store.load_workflow(workflow_id)
    except Exception as exc:
        return None, f"workflow '{workflow_id}' failed to load: {exc}"

    snapshot = template.current_snapshot.model_copy(deep=True)

    # Inject epic/roadmap variables (common requirement in workflows)
    feature = db.backlog.get_feature(feature_id)
    if not feature:
        return None, f"feature not found: {feature_id}"
    epic_id = feature.get("epic_id")
    roadmap_id = feature.get("roadmap_id")
    variables: dict[str, Any] = {}
    if snapshot.workflow_config:
        raw_vars = snapshot.workflow_config.get("variables")
        if isinstance(raw_vars, dict):
            variables.update(raw_vars)
    if epic_id:
        variables["epic_id"] = epic_id
    if roadmap_id:
        variables["roadmap_id"] = roadmap_id

    # Swarm: inject sibling signals so the agent knows what peers have done
    try:
        sibling_signals = db.chain_signals.get_sibling_signals(chain_id, node_id)
        if sibling_signals:
            variables["chain_signals"] = json.dumps(sibling_signals[:20], default=str)
    except Exception:
        logger.debug(
            "Non-critical: sibling signal injection failed for node %s", node_id, exc_info=True
        )

    # Swarm: inject architectural context from knowledge base
    arch_ctx = query_architectural_context(db=db, feature=feature)
    if arch_ctx:
        variables["architectural_context"] = arch_ctx

    if variables:
        workflow_cfg = snapshot.workflow_config or {}
        workflow_cfg["variables"] = variables
        snapshot.workflow_config = workflow_cfg
        snapshot.update_hash()

    # Reuse the caller DB so session rows are written to the same storage DB
    # configuration (standalone pool uses pixl_dir=storage_root).
    session_store = WorkflowSessionStore(storage_root, db=db)
    session = session_store.create_session(feature_id, snapshot)

    worktree_path, branch_name, worktree_error = create_worktree_for_feature(
        project_root,
        feature_id=feature_id,
        base_ref=base_ref,
    )
    if worktree_error or worktree_path is None:
        # Session was created but cannot run without isolation. Clean up to
        # avoid accumulating orphan sessions on repeated dispatch attempts.
        try:
            with db.conn:
                db.conn.execute("DELETE FROM workflow_sessions WHERE id = ?", (session.id,))
        except Exception:
            logger.debug(
                "Non-critical: orphan session cleanup failed for %s", session.id, exc_info=True
            )
        try:
            session_dir = get_sessions_dir(storage_root) / session.id
            if session_dir.exists():
                import shutil

                shutil.rmtree(session_dir, ignore_errors=True)
        except Exception:
            logger.debug(
                "Non-critical: session directory cleanup failed for %s", session.id, exc_info=True
            )
        return None, f"session {session.id}: {worktree_error or 'failed to create worktree'}"
    db.sessions.update_session(session.id, workspace_root=str(worktree_path))

    # Populate worktree context on the session baton for agent awareness
    try:
        worktree_ctx = build_worktree_context(
            db,
            chain_id=chain_id,
            node_id=node_id,
            branch_name=branch_name,
            base_ref=base_ref,
            worktree_path=str(worktree_path),
        )
        session_row = db.sessions.get_session(session.id)
        if session_row:
            baton_raw = session_row.get("baton")
            baton = json.loads(baton_raw) if isinstance(baton_raw, str) else (baton_raw or {})
            if isinstance(baton, dict):
                baton["worktree"] = worktree_ctx
                db.sessions.update_session(session.id, baton=json.dumps(baton))
    except Exception:
        logger.debug(
            "Failed to set worktree context on baton for session %s", session.id, exc_info=True
        )

    if branch_name:
        with contextlib.suppress(Exception):
            db.backlog.update_feature(feature_id, branch_name=branch_name)

    chain_store = ChainPlanDB(db)
    claimed = chain_store.try_claim_node_for_execution(
        chain_id,
        node_id,
        session_id=session.id,
    )
    if not claimed:
        # Another runner claimed it — best-effort cleanup.
        with db.conn:
            db.conn.execute("DELETE FROM workflow_sessions WHERE id = ?", (session.id,))
        return None, "node claim lost"

    thread = threading.Thread(
        target=run_workflow_background,
        kwargs={
            "project_path": storage_root,
            "session_id": session.id,
            "workflow_id": workflow_id,
            "skip_approval": skip_approval,
            "db": db,
        },
        daemon=True,
        name=f"pixl-session:{session.id}",
    )
    thread.start()
    logger.info("Dispatched node %s for chain %s as session %s", node_id, chain_id, session.id)
    return session.id, None

def dispatch_node_pr_retry(
    *,
    db: PixlDB,
    chain_id: str,
    node: dict[str, Any],
) -> tuple[bool, str | None]:
    """Claim a PR-retry node as running with its existing completed session.

    Instead of creating a new workflow session, this just transitions the node
    back to ``running`` with the original ``session_id``.  The reconciliation
    loop in ``run_chain_loop`` will detect the completed session on the next
    tick and enter the PR handling code path directly.

    Returns ``(True, None)`` on success, ``(False, reason)`` on failure.
    On failure the caller should fall back to a full session dispatch.
    """
    store = ChainPlanDB(db)
    node_id = str(node.get("node_id") or "")
    session_id = str(node.get("session_id") or "")
    feature_id = str(node.get("feature_id") or "")

    if not session_id or not feature_id or not node_id:
        return False, "missing required fields for PR retry"

    session_row = db.sessions.get_session(session_id)
    if not session_row:
        return False, f"session not found: {session_id}"
    session_status = str(session_row.get("status", ""))
    if session_status != "completed":
        return False, f"session not completed: {session_status}"

    # Verify the worktree still exists (needed for git push / PR creation).
    workspace_root = str(session_row.get("workspace_root") or "")
    if not workspace_root or not Path(workspace_root).exists():
        return False, "worktree no longer exists"

    # Claim the node — transitions pending → running with original session_id.
    claimed = store.try_claim_node_for_execution(
        chain_id,
        node_id,
        session_id=session_id,
    )
    if not claimed:
        return False, "node claim lost"

    with contextlib.suppress(Exception):
        store.update_node_metadata(
            chain_id,
            node_id,
            updates={"pr_retry": False, "pr_retry_at": datetime.now().isoformat()},
        )

    logger.info(
        "PR retry for node %s (chain %s) reusing session %s",
        node_id,
        chain_id,
        session_id,
    )
    return True, None

def refine_node(
    *,
    db: PixlDB,
    store: ChainPlanDB,
    chain_id: str,
    node: dict[str, Any],
) -> None:
    """Attempt to refine a node by decomposing it into sub-features.

    On success, the node is marked 'refined' and sub-nodes are inserted.
    On failure, the needs_refinement flag is cleared so normal dispatch proceeds.
    """
    node_id = str(node.get("node_id", ""))
    feature_id = str(node.get("feature_id", ""))
    feature = db.backlog.get_feature(feature_id) if feature_id else None
    if not feature:
        logger.warning(
            "Refinement skipped for node %s: feature not found (%s)", node_id, feature_id
        )
        store.update_node_metadata(
            chain_id,
            node_id,
            updates={"needs_refinement": False, "refinement_error": "feature_not_found"},
        )
        return

    logger.info(
        "Refinement requested for node %s (feature=%s, depth=%d) — "
        "agent-based decomposition not yet wired; clearing flag",
        node_id,
        feature.get("title", ""),
        int((node.get("metadata") or {}).get("decomposition_depth", 0)),
    )
    store.update_node_metadata(
        chain_id,
        node_id,
        updates={"needs_refinement": False, "refinement_error": "agent_not_wired"},
    )

def query_architectural_context(
    *,
    db: PixlDB,
    feature: dict[str, Any],
) -> str | None:
    """Query knowledge base for relevant architectural context.

    Returns a markdown section or None if no knowledge index exists.
    """
    try:
        title = str(feature.get("title") or "")
        description = str(feature.get("description") or "")
        query = f"{title} {description}".strip()
        if not query:
            return None

        results = db.knowledge.search(query, limit=5)
        if not results:
            return None

        parts = ["## Architectural Context\n"]
        for chunk in results[:3]:
            content = str(chunk.get("content") or chunk.get("text") or "")
            source = str(chunk.get("source") or chunk.get("path") or "unknown")
            if content:
                parts.append(f"### {source}\n{content[:1000]}\n")

        return "\n".join(parts) if len(parts) > 1 else None
    except Exception:
        return None
