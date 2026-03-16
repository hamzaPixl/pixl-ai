"""Git diff-based contract checks."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePath

from pixl.execution.validation.models import ContractValidationResult, ContractViolation


def check_must_update_files(
    must_update_files: list[str],
    result: ContractValidationResult,
    changed_files: list[str] | set[str] | None,
    git_changed_files_fn: Callable[[ContractValidationResult], set[str] | None],
) -> None:
    """Check that specified files appear in git diff.

    Args:
        must_update_files: List of files expected to be modified
        result: ContractValidationResult to accumulate violations
        changed_files: Pre-resolved changed files, or None to compute via git
        git_changed_files_fn: Callable to get changed files from git
    """
    if changed_files is None:
        changed_files = git_changed_files_fn(result)
        if changed_files is None:
            return  # git unavailable, already recorded

    for pattern in must_update_files:
        if not any(PurePath(f).match(pattern) for f in changed_files):
            result.violations.append(
                ContractViolation(
                    rule="must_update_files",
                    message=f"Expected file to be modified: {pattern}",
                )
            )


def check_max_diff_lines(
    max_diff_lines: int,
    result: ContractValidationResult,
    git_diff_line_count_fn: Callable[[ContractValidationResult], int | None],
) -> None:
    """Check that diff size doesn't exceed limit.

    Args:
        max_diff_lines: Maximum allowed diff lines
        result: ContractValidationResult to accumulate violations
        git_diff_line_count_fn: Callable to get total diff line count
    """
    total_lines = git_diff_line_count_fn(result)
    if total_lines is None:
        return  # git unavailable

    if total_lines > max_diff_lines:
        result.violations.append(
            ContractViolation(
                rule="max_diff_lines",
                message=f"Diff too large: {total_lines} lines (max: {max_diff_lines})",
            )
        )


def check_max_files_changed(
    max_files_changed: int,
    result: ContractValidationResult,
    git_changed_files_fn: Callable[[ContractValidationResult], set[str] | None],
) -> None:
    """Check that number of changed files doesn't exceed limit.

    Args:
        max_files_changed: Maximum allowed number of changed files
        result: ContractValidationResult to accumulate violations
        git_changed_files_fn: Callable to get changed files from git
    """
    changed_files = git_changed_files_fn(result)
    if changed_files is None:
        return  # git unavailable

    if len(changed_files) > max_files_changed:
        result.violations.append(
            ContractViolation(
                rule="max_files_changed",
                message=(
                    f"Too many files changed: {len(changed_files)} (max: {max_files_changed})"
                ),
            )
        )
