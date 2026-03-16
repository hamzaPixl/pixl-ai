"""Quality scoring and consolidation trigger for completed chains."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from pixl.execution.chain.paths import resolve_project_root, resolve_storage_root
from pixl.execution.workflow_background import run_workflow_background
from pixl.storage import WorkflowSessionStore, WorkflowStore
from pixl.storage.db.chain_plans import ChainPlanDB

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)

def record_chain_quality_scores(
    db: PixlDB,
    chain_id: str,
    nodes: list[dict[str, Any]],
) -> None:
    """Record quality metrics when a chain reaches terminal state."""
    try:
        total = len(nodes)
        if total == 0:
            return

        completed = sum(1 for n in nodes if str(n.get("status")) == "completed")
        failed = sum(1 for n in nodes if str(n.get("status")) in {"failed", "blocked", "cancelled"})

        db.quality_scores.record("chain", chain_id, "completion_rate", completed / total)
        db.quality_scores.record("chain", chain_id, "failure_rate", failed / total)
        db.quality_scores.record("chain", chain_id, "total_nodes", float(total))

        # Judge pass rate from signals
        judge_signals = db.chain_signals.get_signals(
            chain_id,
            signal_type="judge_finding",
            limit=100,
        )
        if judge_signals:
            passes = sum(
                1 for s in judge_signals if (s.get("payload") or {}).get("verdict") == "pass"
            )
            db.quality_scores.record(
                "chain",
                chain_id,
                "judge_pass_rate",
                passes / len(judge_signals),
            )
    except Exception:
        logger.debug("Quality score recording failed for chain %s", chain_id, exc_info=True)

def trigger_consolidation_workflow(
    db: PixlDB,
    chain_id: str,
    cfg: dict[str, Any],
) -> None:
    """Start a consolidation workflow session for a completed chain.

    Creates a synthetic feature for the consolidation and dispatches the
    'consolidate' workflow in the background.
    """
    storage_root = resolve_storage_root(db)
    workflow_id = "consolidate"

    workflow_store = WorkflowStore(storage_root)
    try:
        workflow_store.load_workflow(workflow_id)
    except Exception:
        logger.info("Consolidation workflow not available, skipping for chain %s", chain_id)
        return

    chain = ChainPlanDB(db).get_chain(chain_id)
    epic_id = str((chain or {}).get("epic_id", ""))

    session_store = WorkflowSessionStore(storage_root, db=db)
    template = workflow_store.load_workflow(workflow_id)
    snapshot = template.current_snapshot.model_copy(deep=True)

    # Inject chain context as variables
    variables: dict[str, Any] = {"chain_id": chain_id, "epic_id": epic_id}
    base_branch = str(cfg.get("base_branch") or "main")
    variables["base_branch"] = base_branch

    workflow_cfg = snapshot.workflow_config or {}
    workflow_cfg["variables"] = variables
    snapshot.workflow_config = workflow_cfg
    snapshot.update_hash()

    feature_id = f"consolidation-{chain_id}"
    session = session_store.create_session(feature_id, snapshot)

    try:
        from pixl.execution.git_utils import create_worktree_for_feature

        project_root = resolve_project_root(db)
        worktree_path, _branch_name, _wt_error = create_worktree_for_feature(
            project_root, feature_id=feature_id
        )
        if worktree_path:
            db.sessions.update_session(session.id, workspace_root=str(worktree_path))
    except Exception:
        logger.warning(
            "Could not create worktree for consolidation session", exc_info=True
        )

    thread = threading.Thread(
        target=run_workflow_background,
        kwargs={
            "project_path": storage_root,
            "session_id": session.id,
            "workflow_id": workflow_id,
            "skip_approval": False,
            "db": db,
        },
        daemon=True,
        name=f"pixl-consolidate:{chain_id}",
    )
    thread.start()
    logger.info("Started consolidation workflow for chain %s as session %s", chain_id, session.id)

    try:
        db.events.emit(
            event_type="chain_consolidation_started",
            entity_type="chain",
            entity_id=chain_id,
            payload={"session_id": session.id, "workflow_id": workflow_id},
        )
    except Exception:
        logger.debug(
            "Non-critical: consolidation event emission failed for chain %s",
            chain_id,
            exc_info=True,
        )
