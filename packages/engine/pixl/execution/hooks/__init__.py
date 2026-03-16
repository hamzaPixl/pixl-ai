"""Hook system for deterministic Python function execution in workflows.

Hooks are registered Python functions that execute as workflow nodes.
Unlike task nodes (LLM agent calls) or gate nodes (human approval),
hook nodes run deterministic code — e.g., git worktree setup/teardown.

Usage in YAML workflows:
    stages:
      - id: init-git
        name: Initialize Git Worktree
        type: hook
        hook: init-git
        hook_params:
          branch_prefix: "pixl"
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pixl.models.session import WorkflowSession


@dataclass
class HookContext:
    """Context passed to hook functions."""

    session: WorkflowSession
    project_root: Path
    session_dir: Path
    artifacts_dir: Path
    feature_id: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """Result returned by hook functions."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    # If set, executor updates session.workspace_root and its own project_root
    workspace_root: str | None = None


HookFn = Callable[[HookContext], HookResult]

# Built-in hook registry
HOOK_REGISTRY: dict[str, HookFn] = {}


def register_hook(hook_id: str):
    """Decorator to register a built-in hook."""

    def decorator(fn: HookFn) -> HookFn:
        HOOK_REGISTRY[hook_id] = fn
        return fn

    return decorator


def get_hook(hook_id: str) -> HookFn | None:
    """Get a registered hook function by ID."""
    return HOOK_REGISTRY.get(hook_id)


def list_hooks() -> list[str]:
    """List all registered hook IDs."""
    return list(HOOK_REGISTRY.keys())


# Auto-register built-in hooks on import
from pixl.execution.hooks import chain_plan_hooks as _chain_plan_hooks  # noqa: F401, E402
from pixl.execution.hooks import git_hooks as _git_hooks  # noqa: F401, E402
from pixl.execution.hooks import replan_hooks as _replan_hooks  # noqa: F401, E402
from pixl.execution.hooks import roadmap_plan_hooks as _roadmap_plan_hooks  # noqa: F401, E402
from pixl.execution.hooks import sync_hooks as _sync_hooks  # noqa: F401, E402
