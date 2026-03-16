"""Deterministic PR automation via GitHub CLI (`gh`).

This module is designed to be used by the durable chain runner to:
- ensure a branch is committed + pushed
- ensure a PR exists for the branch
- optionally request squash auto-merge

It intentionally does not depend on FastAPI or orchestration/LLM code.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class PRAutomationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PRInfo:
    url: str
    number: int | None = None
    state: str | None = None  # OPEN|MERGED|CLOSED
    merged_at: str | None = None
    base_ref_name: str | None = None
    head_ref_name: str | None = None
    merge_state_status: str | None = None
    is_draft: bool | None = None


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int = 60,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - subprocess failures are platform-specific
        raise PRAutomationError(f"command failed: {cmd}: {exc}") from exc

    if check and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        msg = stderr or stdout or f"exit={proc.returncode}"
        raise PRAutomationError(f"command failed: {' '.join(cmd)}: {msg}")
    return proc


def git_current_branch(worktree_path: Path) -> str:
    proc = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path, timeout=10)
    branch = (proc.stdout or "").strip()
    if not branch or branch == "HEAD":
        raise PRAutomationError("detached HEAD; cannot determine branch name")
    return branch


def git_has_uncommitted_changes(worktree_path: Path) -> bool:
    proc = _run(["git", "status", "--porcelain=v1"], cwd=worktree_path, timeout=10)
    return bool((proc.stdout or "").strip())


def git_commit_all(
    worktree_path: Path,
    *,
    subject: str,
    body: str | None = None,
) -> bool:
    """Stage all changes and create a commit. Returns True if a commit was created."""
    _run(["git", "add", "-A"], cwd=worktree_path, timeout=60)

    cmd = ["git", "commit", "-m", subject]
    if body:
        cmd += ["-m", body]

    proc = _run(cmd, cwd=worktree_path, timeout=120, check=False)
    if proc.returncode == 0:
        return True

    combined = f"{(proc.stdout or '')}\n{(proc.stderr or '')}".lower()
    if "nothing to commit" in combined:
        return False

    raise PRAutomationError((proc.stderr or proc.stdout or "git commit failed").strip())


def git_push_branch(
    worktree_path: Path,
    *,
    remote: str = "origin",
    branch_name: str | None = None,
) -> None:
    branch = branch_name or git_current_branch(worktree_path)
    _run(["git", "push", "-u", remote, branch], cwd=worktree_path, timeout=180)


def try_get_pr_info(worktree_path: Path) -> PRInfo | None:
    fields = [
        "url",
        "number",
        "state",
        "mergedAt",
        "mergeStateStatus",
        "baseRefName",
        "headRefName",
        "isDraft",
    ]
    proc = _run(
        ["gh", "pr", "view", "--json", ",".join(fields)],
        cwd=worktree_path,
        timeout=20,
        check=False,
    )
    if proc.returncode != 0:
        combined = f"{(proc.stdout or '')}\n{(proc.stderr or '')}".lower()
        if "no pull requests found" in combined or "no pull request found" in combined:
            return None
        raise PRAutomationError((proc.stderr or proc.stdout or "gh pr view failed").strip())

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise PRAutomationError(f"gh pr view returned invalid JSON: {exc}") from exc

    url = str(data.get("url") or "").strip()
    if not url:
        return None
    return PRInfo(
        url=url,
        number=(int(data["number"]) if data.get("number") is not None else None),
        state=(str(data.get("state")) if data.get("state") is not None else None),
        merged_at=(str(data.get("mergedAt")) if data.get("mergedAt") is not None else None),
        merge_state_status=(
            str(data.get("mergeStateStatus")) if data.get("mergeStateStatus") is not None else None
        ),
        base_ref_name=(
            str(data.get("baseRefName")) if data.get("baseRefName") is not None else None
        ),
        head_ref_name=(
            str(data.get("headRefName")) if data.get("headRefName") is not None else None
        ),
        is_draft=(bool(data.get("isDraft")) if data.get("isDraft") is not None else None),
    )


def create_pr(
    worktree_path: Path,
    *,
    base_branch: str,
    title: str,
    body_file: Path | None = None,
    body_text: str | None = None,
) -> PRInfo:
    cmd = ["gh", "pr", "create", "--base", base_branch, "--title", title]
    if body_file and body_file.exists():
        cmd += ["--body-file", str(body_file)]
    elif body_text is not None:
        cmd += ["--body", body_text]
    else:
        cmd += ["--body", ""]

    proc = _run(cmd, cwd=worktree_path, timeout=60, check=False)
    if proc.returncode == 0:
        # gh prints the PR URL on stdout in most configurations.
        match = re.search(r"https?://\S+", proc.stdout or "")
        if match:
            url = match.group(0).strip()
            return PRInfo(url=url, state="OPEN")

    # Idempotency: if PR already exists, fall back to view.
    info = try_get_pr_info(worktree_path)
    if info is not None:
        return info

    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    raise PRAutomationError(stderr or stdout or "gh pr create failed")


def request_squash_auto_merge(worktree_path: Path, *, pr_selector: str | None = None) -> None:
    cmd = ["gh", "pr", "merge", "--squash", "--auto", "--delete-branch"]
    if pr_selector:
        cmd.append(pr_selector)
    _run(cmd, cwd=worktree_path, timeout=60)


def pr_merge_state_hint(info: PRInfo | None) -> str:
    if info is None:
        return "no_pr"
    state = (info.state or "").upper()
    if state == "MERGED" or info.merged_at:
        return "merged"
    if state == "CLOSED":
        return "closed"
    merge_state = (info.merge_state_status or "").upper()
    if merge_state in {"BLOCKED", "DIRTY", "BEHIND"}:
        return f"blocked:{merge_state.lower()}"
    return "open"
