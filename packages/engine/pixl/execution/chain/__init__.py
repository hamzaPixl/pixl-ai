"""Chain execution sub-package.

Re-exports the public API for backward compatibility.
"""

from pixl.execution.chain.config import (
    load_chain_exec_config,
    patch_chain_exec_config,
    save_chain_exec_config,
)
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
from pixl.execution.chain.manager import ChainRunnerManager
from pixl.execution.chain.node_executor import (
    build_worktree_context,
    dispatch_node_pr_retry,
    dispatch_node_session,
    query_architectural_context,
    refine_node,
)
from pixl.execution.chain.paths import resolve_project_root, resolve_storage_root
from pixl.execution.chain.pr_manager import ensure_pr_for_node
from pixl.execution.chain.runner import run_chain_loop
from pixl.execution.chain.topology import (
    descendants,
    detect_completed_wave,
    toposort_ready_nodes,
)

__all__ = [
    "ChainRunnerManager",
    "build_worktree_context",
    "check_and_run_judge",
    "descendants",
    "detect_completed_wave",
    "dispatch_node_pr_retry",
    "dispatch_node_session",
    "emit_file_claims",
    "ensure_pr_for_node",
    "extract_and_persist_signals",
    "filter_conflicting_nodes",
    "load_chain_exec_config",
    "patch_chain_exec_config",
    "query_architectural_context",
    "record_chain_quality_scores",
    "refine_node",
    "refresh_file_claims_from_session",
    "resolve_project_root",
    "resolve_storage_root",
    "run_chain_loop",
    "save_chain_exec_config",
    "toposort_ready_nodes",
    "trigger_consolidation_workflow",
]
