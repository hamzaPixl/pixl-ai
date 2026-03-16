"""Recovery sub-package for workflow execution.

Re-exports the public API for backward compatibility.
"""

# contract_repair and patch_and_test are imported lazily by strategies.py
# to avoid circular imports; also re-export here for direct access
from pixl.execution.recovery.contract_repair import (
    attempt_contract_repair,
    finalize_repair_success,
)
from pixl.execution.recovery.error_classifier import (
    error_from_result,
    extract_affected_files_from_diff,
    extract_diff_from_output,
)
from pixl.execution.recovery.helpers import (
    _build_step_result,
    _maybe_finalize_terminal,
    escalate_recovery,
    pause_for_human,
    write_human_blocker_artifact,
)
from pixl.execution.recovery.missing_input import (
    attempt_missing_input_recovery,
    collect_path_nodes,
    infer_missing_input_producers,
    reset_nodes_for_reexecution,
    write_missing_input_feedback,
)
from pixl.execution.recovery.patch_and_test import (
    attempt_patch_and_test,
)
from pixl.execution.recovery_handler import (
    handle_pixl_error,
    reset_node_for_retry,
    try_recovery_for_result,
)

__all__ = [
    "_build_step_result",
    "_maybe_finalize_terminal",
    "attempt_contract_repair",
    "attempt_missing_input_recovery",
    "attempt_patch_and_test",
    "collect_path_nodes",
    "error_from_result",
    "escalate_recovery",
    "extract_affected_files_from_diff",
    "extract_diff_from_output",
    "finalize_repair_success",
    "handle_pixl_error",
    "infer_missing_input_producers",
    "pause_for_human",
    "reset_node_for_retry",
    "reset_nodes_for_reexecution",
    "try_recovery_for_result",
    "write_human_blocker_artifact",
    "write_missing_input_feedback",
]
