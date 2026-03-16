"""Git lifecycle hooks for workflow execution.

Provides init-git (create worktree + branch) and finalize-git (cleanup)
hooks that enable workflows to automatically isolate work in git worktrees.
"""

import subprocess

from pixl.execution.hooks import HookContext, HookResult, register_hook

@register_hook("init-git")
def init_git_hook(ctx: HookContext) -> HookResult:
    """Create a git worktree + branch for this workflow session."""
    prefix = ctx.params.get("branch_prefix", "pixl")
    feature_id = ctx.feature_id
    session_id = ctx.session.id

    branch_name = f"{prefix}/{feature_id}/{session_id}"
    worktree_dir = ctx.project_root / ".pixl" / "worktrees" / session_id

    if worktree_dir.exists():
        return HookResult(
            success=True,
            workspace_root=str(worktree_dir),
            data={
                "branch": branch_name,
                "worktree": str(worktree_dir),
                "reused": True,
            },
        )

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(ctx.project_root),
            timeout=10,
        )
        if head.returncode != 0:
            return HookResult(
                success=False,
                error=f"git rev-parse HEAD failed: {head.stderr}",
            )

        base_commit = head.stdout.strip()

        subprocess.run(
            ["git", "branch", branch_name, base_commit],
            capture_output=True,
            text=True,
            cwd=str(ctx.project_root),
            timeout=10,
        )

        worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), branch_name],
            capture_output=True,
            text=True,
            cwd=str(ctx.project_root),
            timeout=30,
        )
        if result.returncode != 0:
            return HookResult(
                success=False,
                error=f"git worktree add failed: {result.stderr}",
            )

        return HookResult(
            success=True,
            workspace_root=str(worktree_dir),
            data={
                "branch": branch_name,
                "worktree": str(worktree_dir),
                "base_commit": base_commit,
            },
        )
    except subprocess.TimeoutExpired:
        return HookResult(success=False, error="git command timed out")
    except Exception as e:
        return HookResult(success=False, error=str(e))

@register_hook("finalize-git")
def finalize_git_hook(ctx: HookContext) -> HookResult:
    """Remove the git worktree created by init-git."""
    worktree_dir = ctx.project_root / ".pixl" / "worktrees" / ctx.session.id

    # Determine the original project root (parent of .pixl/worktrees/)
    original_root = ctx.project_root
    if ".pixl" in str(ctx.project_root) and "worktrees" in str(ctx.project_root):
        # We're inside a worktree — go up to find original repo
        original_root = ctx.project_root.parent.parent.parent

    if not worktree_dir.exists():
        return HookResult(success=True, data={"already_cleaned": True})

    try:
        result = subprocess.run(
            ["git", "worktree", "remove", str(worktree_dir), "--force"],
            capture_output=True,
            text=True,
            cwd=str(original_root),
            timeout=30,
        )
        if result.returncode != 0:
            return HookResult(
                success=False,
                error=f"git worktree remove failed: {result.stderr}",
            )

        return HookResult(
            success=True,
            workspace_root=str(original_root),
            data={"removed": str(worktree_dir)},
        )
    except Exception as e:
        return HookResult(success=False, error=str(e))
