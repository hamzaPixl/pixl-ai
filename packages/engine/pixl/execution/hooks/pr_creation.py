"""Auto-PR hook — creates a pull request on workflow completion.

Runs ``git push`` + ``gh pr create`` inside the sandbox (or locally)
when a workflow reaches the finalize stage with sufficient confidence.

Workflow YAML usage::

    - id: finalize
      type: hook
      hook: create-pr
      hook_params:
        auto_merge: false
        reviewers: ["@team"]
        draft: true
        base_branch: main
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class PRConfig:
    """Configuration for auto-PR creation."""

    auto_merge: bool = False
    draft: bool = True
    base_branch: str = "main"
    reviewers: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    title: str | None = None  # auto-generated from feature if None
    body: str | None = None  # auto-generated from session summary if None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PRConfig:
        return cls(
            auto_merge=bool(data.get("auto_merge", False)),
            draft=bool(data.get("draft", True)),
            base_branch=str(data.get("base_branch", "main")),
            reviewers=data.get("reviewers", []),
            labels=data.get("labels", []),
            title=data.get("title"),
            body=data.get("body"),
        )

@dataclass
class PRResult:
    """Result of PR creation."""

    success: bool
    pr_url: str | None = None
    error: str | None = None
    branch: str | None = None

def create_pr(
    project_root: Path,
    *,
    config: PRConfig | None = None,
    session_id: str | None = None,
    feature_title: str | None = None,
    session_summary: str | None = None,
) -> PRResult:
    """Push current branch and create a PR via ``gh``.

    Args:
        project_root: Path to the git repository.
        config: PR creation configuration.
        session_id: Session ID for branch naming.
        feature_title: Feature title for PR title.
        session_summary: Session summary for PR body.
    """
    config = config or PRConfig()

    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=True,
        ).stdout.strip()

        if branch in ("main", "master"):
            return PRResult(
                success=False,
                error="Cannot create PR from main/master branch",
                branch=branch,
            )

        # Check for uncommitted changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=project_root,
        ).stdout.strip()

        if status:
            # Auto-commit remaining changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=project_root,
                check=True,
            )
            commit_msg = f"chore: finalize session {session_id or 'unknown'}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=project_root,
                check=True,
            )

        # Push branch
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )

        title = config.title or feature_title or f"feat: {branch}"
        body = config.body or session_summary or "Auto-generated PR from pixl workflow."

        cmd = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", config.base_branch,
        ]

        if config.draft:
            cmd.append("--draft")

        for reviewer in config.reviewers:
            cmd.extend(["--reviewer", reviewer.lstrip("@")])

        for label in config.labels:
            cmd.extend(["--label", label])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
            check=True,
        )

        pr_url = result.stdout.strip()
        logger.info("Created PR: %s", pr_url)

        # Auto-merge if configured
        if config.auto_merge and pr_url:
            subprocess.run(
                ["gh", "pr", "merge", pr_url, "--auto", "--squash"],
                cwd=project_root,
                capture_output=True,
            )

        return PRResult(success=True, pr_url=pr_url, branch=branch)

    except subprocess.CalledProcessError as exc:
        error_msg = exc.stderr or exc.stdout or str(exc)
        logger.error("PR creation failed: %s", error_msg)
        return PRResult(success=False, error=error_msg)
    except FileNotFoundError as exc:
        error_msg = f"Required tool not found: {exc}"
        logger.error(error_msg)
        return PRResult(success=False, error=error_msg)
