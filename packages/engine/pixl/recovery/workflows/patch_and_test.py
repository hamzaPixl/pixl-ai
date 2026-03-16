"""Patch + Test Loop: Safe code-level auto-correct system.

Accepts LLM-proposed diffs, validates constraints (diff limits, protected paths),
applies patches in a git worktree sandbox, runs tests, and auto-applies only if
tests pass AND constraints are satisfied. Escalates to human approval for
protected paths or failed tests.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pixl.errors import PixlError

# Data Models

@dataclass(frozen=True)
class PatchProposal:
    """LLM-proposed patch with metadata.

    Attributes:
        diff: Unified diff format patch content
        affected_files: List of files that will be modified
        description: Human-readable description of the change
        confidence: LLM confidence level (0-1), default 0.5
    """

    diff: str
    affected_files: list[str]
    description: str
    confidence: float = 0.5

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"PatchProposal confidence must be between 0 and 1, got {self.confidence}"
            )

@dataclass(frozen=True)
class PatchConstraints:
    """Constraints for patch validation.

    Attributes:
        max_diff_lines: Maximum allowed insertions + deletions
        protected_paths: Paths that cannot be modified without escalation
        allowed_paths: If set, only these paths can be modified (None = no restriction)
        require_tests: Whether tests must pass to auto-apply
        auto_apply_confidence_threshold: Minimum confidence for auto-apply
    """

    max_diff_lines: int = 100
    protected_paths: list[str] = field(
        default_factory=lambda: [
            "src/pixl/core/",
            ".pixl/",
            "pyproject.toml",
        ]
    )
    allowed_paths: list[str] | None = None
    require_tests: bool = True
    auto_apply_confidence_threshold: float = 0.7

@dataclass
class PatchResult:
    """Result of patch evaluation and application.

    Attributes:
        applied: Whether the patch was applied to the main repository
        tests_passed: Test results (None if tests not run)
        violations: List of constraint violations found
        escalated: Whether escalation to human was required
        test_results: Detailed test results dict
        reason: Human-readable explanation of the outcome
        sandbox_path: Path to sandbox worktree (if created)
        sandbox_cleanup_required: Whether sandbox needs manual cleanup
    """

    applied: bool
    tests_passed: bool | None
    violations: list[str]
    escalated: bool
    test_results: dict[str, Any] | None
    reason: str
    sandbox_path: Path | None = None
    sandbox_cleanup_required: bool = False

# Constraint Validation

def count_diff_lines(diff: str) -> int:
    """Parse unified diff format to count insertions + deletions.

    Args:
        diff: Unified diff content

    Returns:
        Total number of insertions and deletions

    Examples:
        >>> count_diff_lines("@@ -1 +1 @@\\n-old\\n+new")
        2
    """
    total = 0
    for line in diff.splitlines():
        # Lines starting with '+' (not '+++' header) are insertions
        if (
            line.startswith("+")
            and not line.startswith("+++")
            or line.startswith("-")
            and not line.startswith("---")
        ):
            total += 1
    return total

def touches_protected_path(
    affected_files: list[str],
    constraints: PatchConstraints,
) -> bool:
    """Check if any affected file is in a protected path.

    Args:
        affected_files: List of file paths to check
        constraints: Constraints with protected_paths patterns

    Returns:
        True if any file matches a protected path pattern
    """
    for file_path in affected_files:
        file_path_normalized = file_path.replace("\\", "/")
        for protected in constraints.protected_paths:
            protected_normalized = protected.replace("\\", "/")
            # Check prefix match for directories, exact match for files
            if (
                file_path_normalized.startswith(protected_normalized.rstrip("/") + "/")
                or file_path_normalized == protected_normalized
            ):
                return True
    return False

def within_allowed_paths(
    affected_files: list[str],
    constraints: PatchConstraints,
) -> bool:
    """Check if all affected files are within allowed paths.

    Args:
        affected_files: List of file paths to check
        constraints: Constraints with allowed_paths patterns

    Returns:
        True if all files match at least one allowed path pattern,
        or if allowed_paths is None (no restriction)
    """
    if constraints.allowed_paths is None:
        return True

    if not affected_files:
        return True

    for file_path in affected_files:
        file_path_normalized = file_path.replace("\\", "/")
        matched = False
        for allowed in constraints.allowed_paths:
            allowed_normalized = allowed.replace("\\", "/")
            if (
                file_path_normalized.startswith(allowed_normalized.rstrip("/") + "/")
                or file_path_normalized == allowed_normalized
            ):
                matched = True
                break
        if not matched:
            return False
    return True

def extract_files_from_diff(diff: str) -> list[str]:
    """Extract actual file paths from unified diff content.

    Parses diff headers (--- a/path and +++ b/path) to get the real
    files being modified. This prevents spoofing via affected_files.

    Args:
        diff: Unified diff content

    Returns:
        List of unique file paths found in the diff
    """
    import re

    files: set[str] = set()
    # Match both --- a/path and +++ b/path headers
    # Also handle --- /dev/null for new files and +++ /dev/null for deletions
    pattern = re.compile(r"^(?:---|\+\+\+) (?:a/|b/)?(.+)$", re.MULTILINE)

    for match in pattern.finditer(diff):
        path = match.group(1).strip()
        # Skip /dev/null (used for new/deleted files)
        if path != "/dev/null" and not path.startswith("/dev/null"):
            files.add(path)

    return list(files)

def validate_constraints(
    proposal: PatchProposal,
    constraints: PatchConstraints,
) -> list[str]:
    """Validate patch against all constraints.

    Args:
        proposal: The patch proposal to validate
        constraints: Constraints to check against

    Returns:
        List of violation messages (empty if valid)
    """
    violations: list[str] = []

    # Check diff size
    diff_lines = count_diff_lines(proposal.diff)
    if diff_lines > constraints.max_diff_lines:
        violations.append(f"Diff too large: {diff_lines} lines (max: {constraints.max_diff_lines})")

    # SECURITY: Extract actual files from diff, don't trust affected_files
    actual_files = extract_files_from_diff(proposal.diff)

    declared_set = set(proposal.affected_files)
    actual_set = set(actual_files)
    undeclared_files = actual_set - declared_set
    if undeclared_files:
        violations.append(
            f"Diff modifies undeclared files (possible spoofing): {sorted(undeclared_files)}"
        )

    # Check protected paths using ACTUAL files from diff
    if touches_protected_path(actual_files, constraints):
        violations.append(f"Patch touches protected paths: {constraints.protected_paths}")

    # Check allowed paths using ACTUAL files from diff
    if not within_allowed_paths(actual_files, constraints):
        violations.append(f"Patch affects files outside allowed paths: {constraints.allowed_paths}")

    return violations

# Sandbox Operations

def create_sandbox_worktree(
    project_root: Path,
    session_id: str,
) -> tuple[Path, str] | tuple[None, None]:
    """Create a git worktree sandbox for testing patches.

    Args:
        project_root: Path to the git repository
        session_id: Unique session identifier for the worktree

    Returns:
        Tuple of (worktree_path, branch_name) or (None, None) on failure
    """
    worktree_dir = project_root / ".pixl" / "worktrees" / session_id
    branch_name = f"pixl/patch-test/{session_id}"

    # Reuse existing worktree
    if worktree_dir.exists():
        return worktree_dir, branch_name

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=10,
        )
        if head.returncode != 0:
            return None, None

        base_commit = head.stdout.strip()

        subprocess.run(
            ["git", "branch", branch_name, base_commit],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=10,
        )

        worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), branch_name],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )
        if result.returncode != 0:
            return None, None

        return worktree_dir, branch_name
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None, None

def remove_sandbox_worktree(
    project_root: Path,
    session_id: str,
) -> bool:
    """Remove a git worktree sandbox.

    Args:
        project_root: Path to the original git repository
        session_id: Session identifier for the worktree to remove

    Returns:
        True if successful, False otherwise
    """
    worktree_dir = project_root / ".pixl" / "worktrees" / session_id

    if not worktree_dir.exists():
        return True

    try:
        result = subprocess.run(
            ["git", "worktree", "remove", str(worktree_dir), "--force"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False

def apply_patch_in_sandbox(
    worktree_root: Path,
    diff: str,
) -> tuple[bool, str]:
    """Apply a unified diff patch in the sandbox worktree.

    Args:
        worktree_root: Path to the sandbox worktree
        diff: Unified diff content to apply

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # First check if the patch applies cleanly
        check_result = subprocess.run(
            ["git", "apply", "--check", "-"],
            input=diff,
            capture_output=True,
            text=True,
            cwd=str(worktree_root),
            timeout=10,
        )
        if check_result.returncode != 0:
            return False, check_result.stderr or check_result.stdout

        apply_result = subprocess.run(
            ["git", "apply", "-"],
            input=diff,
            capture_output=True,
            text=True,
            cwd=str(worktree_root),
            timeout=10,
        )
        if apply_result.returncode != 0:
            return False, apply_result.stderr or apply_result.stdout

        return True, ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return False, str(e)

def run_tests(
    worktree_root: Path,
    test_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Run pytest in the sandbox worktree.

    Args:
        worktree_root: Path to the sandbox worktree
        test_paths: Optional list of specific test paths to run

    Returns:
        Dict with keys: exit_code, passed, output, summary
    """
    cmd = ["pytest", "-q", "--tb=no"]
    if test_paths:
        cmd.extend(test_paths)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(worktree_root),
            timeout=60,
        )

        output = result.stdout + result.stderr

        summary = ""
        passed = result.returncode == 0

        # Look for summary patterns like "3 passed, 1 failed"
        for line in output.splitlines():
            if " passed" in line or " failed" in line or " error" in line:
                summary = line.strip()
                break

        if not summary:
            summary = "tests passed" if passed else "tests failed"

        return {
            "exit_code": result.returncode,
            "passed": passed,
            "output": output,
            "summary": summary,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "passed": False,
            "output": "Tests timed out after 60 seconds",
            "summary": "timeout",
        }
    except (FileNotFoundError, OSError) as e:
        return {
            "exit_code": -1,
            "passed": False,
            "output": str(e),
            "summary": "error",
        }

def should_auto_apply(
    proposal: PatchProposal,
    constraints: PatchConstraints,
    violations: list[str],
    test_results: dict[str, Any] | None,
) -> bool:
    """Determine if patch should be auto-applied.

    Auto-apply only if ALL conditions are met:
    1. No constraint violations
    2. Tests passed (if tests required)
    3. Confidence >= threshold

    Args:
        proposal: The patch proposal
        constraints: Constraints to check
        violations: List of constraint violations
        test_results: Test results (None if tests not run)

    Returns:
        True if patch should be auto-applied
    """
    if violations:
        return False

    if constraints.require_tests and (not test_results or not test_results.get("passed")):
        return False

    return not proposal.confidence < constraints.auto_apply_confidence_threshold

def execute(
    proposal: PatchProposal,
    constraints: PatchConstraints,
    project_root: Path,
    session_id: str,
    test_paths: list[str] | None = None,
) -> PatchResult:
    """Main orchestration: validate, sandbox test, and apply patch.

    Args:
        proposal: The patch proposal to evaluate
        constraints: Validation constraints
        project_root: Path to the project repository
        session_id: Unique session identifier
        test_paths: Optional specific test paths to run

    Returns:
        PatchResult with outcome and metadata
    """
    violations = validate_constraints(proposal, constraints)

    if violations:
        return PatchResult(
            applied=False,
            tests_passed=None,
            violations=violations,
            escalated=True,
            test_results=None,
            reason=f"Constraint violations: {', '.join(violations)}",
        )

    worktree_path, branch_name = create_sandbox_worktree(project_root, session_id)

    if worktree_path is None:
        return PatchResult(
            applied=False,
            tests_passed=None,
            violations=violations,
            escalated=True,
            test_results=None,
            reason="Failed to create sandbox worktree",
        )

    patch_success, patch_error = apply_patch_in_sandbox(worktree_path, proposal.diff)

    if not patch_success:
        remove_sandbox_worktree(project_root, session_id)
        return PatchResult(
            applied=False,
            tests_passed=None,
            violations=[f"Patch apply failed: {patch_error}"],
            escalated=True,
            test_results=None,
            reason=f"Patch failed to apply: {patch_error}",
        )

    test_results: dict[str, Any] | None = None
    if constraints.require_tests:
        test_results = run_tests(worktree_path, test_paths)

    should_apply = should_auto_apply(proposal, constraints, violations, test_results)

    applied = False
    escalated = False

    if should_apply:
        try:
            apply_result = subprocess.run(
                ["git", "apply", "-"],
                input=proposal.diff,
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=10,
            )
            applied = apply_result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            applied = False

        if not applied:
            escalated = True

    else:
        # Determine escalation reason
        if (
            constraints.require_tests
            and test_results
            and not test_results.get("passed")
            or proposal.confidence < constraints.auto_apply_confidence_threshold
        ):
            escalated = True

    cleanup_success = remove_sandbox_worktree(project_root, session_id)

    reason_parts = []
    if applied:
        reason_parts.append("Patch applied successfully")
    elif test_results and not test_results.get("passed"):
        reason_parts.append(f"Tests failed: {test_results.get('summary', 'unknown')}")
    elif proposal.confidence < constraints.auto_apply_confidence_threshold:
        reason_parts.append(
            f"Confidence below threshold: {proposal.confidence} < "
            f"{constraints.auto_apply_confidence_threshold}"
        )

    reason = "; ".join(reason_parts) if reason_parts else "Patch not applied"

    return PatchResult(
        applied=applied,
        tests_passed=test_results.get("passed") if test_results else None,
        violations=violations,
        escalated=escalated,
        test_results=test_results,
        reason=reason,
        sandbox_path=worktree_path if not cleanup_success else None,
        sandbox_cleanup_required=not cleanup_success,
    )

class PatchAndTestError(PixlError):
    """Error raised during patch-and-test workflow."""

    def __init__(
        self,
        message: str,
        *,
        proposal: PatchProposal | None = None,
        result: PatchResult | None = None,
        cause: Exception | None = None,
    ) -> None:
        metadata: dict[str, Any] = {}
        if proposal:
            metadata["affected_files"] = proposal.affected_files
            metadata["confidence"] = proposal.confidence
        if result:
            metadata["violations"] = result.violations
            metadata["escalated"] = result.escalated

        super().__init__(
            "patch_and_test_error",
            message,
            cause=cause,
            metadata=metadata,
        )
        self.proposal = proposal
        self.result = result
