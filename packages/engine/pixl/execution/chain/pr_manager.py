"""PR creation and auto-merge for chain nodes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pixl.execution.chain.paths import resolve_storage_root
from pixl.execution.workflow_helpers import ensure_pr_for_feature
from pixl.git import pr_automation

if TYPE_CHECKING:
    from pixl.storage.db.chain_plans import ChainPlanDB
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)


def ensure_pr_for_node(
    *,
    db: PixlDB,
    chain_store: ChainPlanDB,
    chain_id: str,
    node_id: str,
    feature_id: str,
    session_id: str,
    worktree_path: Path,
    base_remote: str,
    base_branch: str,
) -> pr_automation.PRInfo:
    """Ensure a PR exists for the given chain node, creating one if necessary.

    Delegates core PR creation to the shared ``ensure_pr_for_feature`` helper,
    then adds chain-specific node metadata updates.
    """
    storage_root = resolve_storage_root(db)

    info = ensure_pr_for_feature(
        db=db,
        feature_id=feature_id,
        session_id=session_id,
        worktree_path=worktree_path,
        storage_root=storage_root,
        base_branch=base_branch,
        base_remote=base_remote,
        extra_trailers=f"Pixl-Chain: {chain_id}",
    )
    if info is None:
        msg = f"No PR created for node {node_id} (feature {feature_id})"
        raise pr_automation.PRAutomationError(msg)

    # Chain-specific: persist PR metadata on the node for chain UI/projections.
    try:
        branch_name = pr_automation.git_current_branch(worktree_path)
        chain_store.update_node_metadata(
            chain_id,
            node_id,
            updates={
                "branch_name": branch_name,
                "pr_url": info.url,
            },
        )
    except Exception:
        logger.debug(
            "Non-critical: node metadata update failed for %s:%s", chain_id, node_id, exc_info=True
        )

    return info
