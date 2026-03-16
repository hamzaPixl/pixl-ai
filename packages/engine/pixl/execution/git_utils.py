"""Shared git subprocess utilities for the execution layer.

Extracted from chain_runner.py and contract_validator.py to eliminate
duplicated subprocess calls and provide a single place for git operations.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

def git_set_remote(project_path: Path, name: str, url: str) -> tuple[bool, str | None]:
    """Add or update a git remote.

    Returns (success, error).
    """
    try:
        if git_has_remote(project_path, name):
            result = subprocess.run(
                ["git", "remote", "set-url", name, url],
                capture_output=True,
                text=True,
                cwd=str(project_path),
                timeout=10,
            )
        else:
            result = subprocess.run(
                ["git", "remote", "add", name, url],
                capture_output=True,
                text=True,
                cwd=str(project_path),
                timeout=10,
            )
    except Exception as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "git remote failed").strip()
    return True, None


def git_clone(url: str, target_path: Path, branch: str | None = None) -> tuple[bool, str | None]:
    """Clone a git repository.

    Returns (success, error).
    """
    cmd = ["git", "clone", url, str(target_path)]
    if branch:
        cmd.extend(["--branch", branch])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "git clone failed").strip()
    return True, None


def git_symbolic_head(project_path: Path) -> tuple[str | None, str | None]:
    """Get the current branch name via symbolic-ref.

    Returns (branch_name, error). On detached HEAD returns (None, "detached_head").
    """
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )
    except Exception as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, (result.stderr or result.stdout or "git symbolic-ref failed").strip()
    branch = (result.stdout or "").strip()
    if not branch or branch == "HEAD":
        return None, "detached_head"
    return branch, None

def git_rev_parse(project_path: Path, ref: str) -> tuple[str | None, str | None]:
    """Resolve a git ref to a commit hash.

    Returns (commit_hash, error).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", ref],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )
    except Exception as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, (result.stderr or result.stdout or "git rev-parse failed").strip()
    return (result.stdout or "").strip(), None

def git_fetch(project_path: Path, *, remote: str, branch: str) -> tuple[bool, str | None]:
    """Fetch a branch from a remote.

    Returns (success, error).
    """
    try:
        result = subprocess.run(
            ["git", "fetch", remote, branch],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=60,
        )
    except Exception as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "git fetch failed").strip()
    return True, None

def git_has_remote(project_path: Path, remote: str) -> bool:
    """Check whether a named remote exists."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", remote],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )
    except Exception:
        return False
    return result.returncode == 0

def refresh_base_ref(
    project_path: Path,
    *,
    remote: str,
    base_branch: str,
) -> tuple[str | None, str | None]:
    """Fetch and resolve the latest commit for *remote/base_branch*.

    Returns (commit_hash, error).
    """
    ok, err = git_fetch(project_path, remote=remote, branch=base_branch)
    if not ok:
        return None, err
    ref, err = git_rev_parse(project_path, f"{remote}/{base_branch}")
    if err or not ref:
        return None, err or "failed_to_resolve_base_ref"
    return ref, None

def ensure_git_available(project_path: Path) -> tuple[bool, str | None]:
    """Quick check that git is usable in *project_path*.

    Returns (available, error).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )
    except Exception as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "git rev-parse failed").strip()
    return True, None

def _branch_exists_local(project_path: Path, branch_name: str) -> bool:
    """Check if a local branch exists."""
    try:
        result = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )
    except Exception:
        return False
    return result.returncode == 0

def _ensure_project_git_repo(
    project_path: Path,
    remote_url: str | None = None,
) -> tuple[Path, str | None]:
    """Ensure *project_path* is the root of its own git repository.

    If the directory already contains a ``.git``, return it as-is.
    If git walks up and finds a *parent* repo (e.g. ``~/.pixl/.git``),
    initialise a new isolated repo inside *project_path* so that
    branches and worktrees are fully scoped to this project.

    If *remote_url* is provided, sets it as the ``origin`` remote.

    Returns (git_root, error).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )
    except Exception as exc:
        return project_path, str(exc)

    if result.returncode == 0:
        git_root = Path(result.stdout.strip())
        if git_root.resolve() == project_path.resolve():
            if remote_url:
                git_set_remote(project_path, "origin", remote_url)
            return project_path, None  # Already its own repo — nothing to do.

    # Either no repo found or a parent repo owns it → init a project-scoped one.
    logger.info("Initialising isolated git repo for project at %s", project_path)
    init = subprocess.run(
        ["git", "init"],
        capture_output=True,
        text=True,
        cwd=str(project_path),
        timeout=10,
    )
    if init.returncode != 0:
        return project_path, f"git init failed: {init.stderr}".strip()

    # Seed with an initial commit so HEAD exists and worktrees can branch from it.
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "pixl: project initialised"],
        capture_output=True,
        text=True,
        cwd=str(project_path),
        timeout=10,
    )

    if remote_url:
        ok, err = git_set_remote(project_path, "origin", remote_url)
        if not ok:
            logger.warning("Failed to set remote origin: %s", err)

    return project_path, None

def create_worktree_for_feature(
    project_path: Path,
    *,
    feature_id: str,
    base_ref: str | None = None,
    branch_prefix: str = "pixl",
) -> tuple[Path | None, str | None, str | None]:
    """Create (or reuse) a worktree for a feature.

    Unlike session-based worktrees, this uses a single branch and worktree
    per feature so multiple sessions accumulate work on the same branch.

    Each project gets its own git repository (initialised lazily if needed)
    so that branches, worktrees, and history are fully isolated per project.

    Returns (worktree_path, branch_name, error).
    """
    # a shared parent like ~/.pixl).  This makes branches/worktrees fully
    # project-scoped without needing slug prefixes.
    _, init_err = _ensure_project_git_repo(project_path)
    if init_err:
        return None, None, f"git repo init failed: {init_err}"

    worktree_dir = project_path / ".pixl" / "worktrees" / feature_id
    branch_name = f"{branch_prefix}/{feature_id}"

    # Idempotent: reuse existing worktree
    if worktree_dir.exists():
        return worktree_dir, branch_name, None

    try:
        # If branch already exists (previous session created it), just attach worktree
        if _branch_exists_local(project_path, branch_name):
            worktree_dir.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "worktree", "add", str(worktree_dir), branch_name],
                capture_output=True,
                text=True,
                cwd=str(project_path),
                timeout=30,
            )
            if result.returncode != 0:
                return None, None, f"git worktree add failed: {result.stderr}".strip()
            return worktree_dir, branch_name, None

        # New branch: resolve base and create
        ref = base_ref or "HEAD"
        head = subprocess.run(
            ["git", "rev-parse", ref],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )
        if head.returncode != 0:
            return None, None, f"git rev-parse {ref} failed: {head.stderr}".strip()
        base_commit = head.stdout.strip()

        subprocess.run(
            ["git", "branch", branch_name, base_commit],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=10,
        )

        worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), branch_name],
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=30,
        )
        if result.returncode != 0:
            return None, None, f"git worktree add failed: {result.stderr}".strip()
        return worktree_dir, branch_name, None
    except subprocess.TimeoutExpired:
        return None, None, "git command timed out"
    except Exception as exc:
        return None, None, str(exc)

def auto_push_feature_branch(
    worktree_path: Path,
    *,
    feature_id: str,
    remote: str = "origin",
) -> tuple[bool, str | None]:
    """Safety-commit uncommitted changes and push the feature branch.

    No-ops gracefully if the worktree is clean or no remote exists.
    Returns (pushed, error).
    """
    try:
        if not git_has_remote(worktree_path, remote):
            return False, None  # No remote — not an error

        # Check for uncommitted changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(worktree_path),
            timeout=10,
        )
        if status.returncode != 0:
            return False, f"git status failed: {status.stderr}".strip()

        if status.stdout.strip():
            # Safety commit
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                text=True,
                cwd=str(worktree_path),
                timeout=30,
            )
            subprocess.run(
                ["git", "commit", "-m", f"pixl: safety commit for {feature_id}"],
                capture_output=True,
                text=True,
                cwd=str(worktree_path),
                timeout=30,
            )

        branch_result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(worktree_path),
            timeout=10,
        )
        if branch_result.returncode != 0:
            return False, "detached HEAD — cannot push"
        branch = branch_result.stdout.strip()

        # Push
        push = subprocess.run(
            ["git", "push", "-u", remote, branch],
            capture_output=True,
            text=True,
            cwd=str(worktree_path),
            timeout=60,
        )
        if push.returncode != 0:
            return False, f"git push failed: {push.stderr}".strip()

        return True, None
    except subprocess.TimeoutExpired:
        return False, "git push timed out"
    except Exception as exc:
        return False, str(exc)

def cleanup_feature_worktree(project_path: Path, feature_id: str) -> None:
    """Remove the worktree for a feature (keeps the branch)."""
    worktree_dir = project_path / ".pixl" / "worktrees" / feature_id
    if not worktree_dir.exists():
        return
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_dir)],
        cwd=str(project_path),
        check=False,
        capture_output=True,
    )
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)

def git_changed_files(
    project_root: Path,
    baseline_commit: str,
) -> tuple[set[str] | None, str | None]:
    """Get set of changed files from git diff against a baseline commit.

    Returns (changed_files, error_message). Returns (None, error) if git unavailable.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", f"{baseline_commit}..HEAD", "--name-only"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=10,
        )
        if proc.returncode != 0:
            return None, f"git diff failed: {proc.stderr.strip()}"

        return {line.strip() for line in proc.stdout.splitlines() if line.strip()}, None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None, "git command not available"

def git_diff_line_count(
    project_root: Path,
    baseline_commit: str,
) -> tuple[int | None, str | None]:
    """Get total diff line count (insertions + deletions).

    Returns (line_count, error_message). Returns (None, error) if git unavailable.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", f"{baseline_commit}..HEAD", "--numstat"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=10,
        )
        if proc.returncode != 0:
            return None, f"git diff --numstat failed: {proc.stderr.strip()}"

        total = 0
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                insertions = parts[0].strip()
                deletions = parts[1].strip()
                # Skip binary files (shown as '-')
                if insertions != "-" and deletions != "-":
                    total += int(insertions) + int(deletions)
        return total, None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None, "git command not available"
