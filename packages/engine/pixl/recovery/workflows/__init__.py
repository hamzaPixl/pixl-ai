"""Recovery workflow modules."""

from pixl.recovery.workflows.contract_repair import (
    ContractRepairResult,
    ContractRepairWorkflow,
)
from pixl.recovery.workflows.patch_and_test import (
    PatchAndTestError,
    PatchConstraints,
    PatchProposal,
    PatchResult,
    apply_patch_in_sandbox,
    count_diff_lines,
    create_sandbox_worktree,
    execute,
    remove_sandbox_worktree,
    run_tests,
    should_auto_apply,
    touches_protected_path,
    validate_constraints,
    within_allowed_paths,
)

__all__ = [
    "ContractRepairResult",
    "ContractRepairWorkflow",
    "PatchProposal",
    "PatchConstraints",
    "PatchResult",
    "PatchAndTestError",
    "count_diff_lines",
    "touches_protected_path",
    "within_allowed_paths",
    "validate_constraints",
    "create_sandbox_worktree",
    "remove_sandbox_worktree",
    "apply_patch_in_sandbox",
    "run_tests",
    "should_auto_apply",
    "execute",
]
