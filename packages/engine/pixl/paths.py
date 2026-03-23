"""Helpers for resolving Pixl storage paths.

All project data lives under the standalone global workspace at
~/.pixl/projects/<project-id>/.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


def _slugify(value: str) -> str:
    """Normalize a string for use in filesystem paths."""
    name = value.lower().replace("_", "-").replace(" ", "-")
    name = re.sub(r"[^a-z0-9-]", "", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "default"


def canonical_project_root(project_path: Path) -> Path:
    """Return the canonical project root for Pixl storage.

    Pixl can execute workflows inside git worktrees located under:
      <repo>/.pixl/worktrees/<session_id>/

    In that case, storage (DB, sessions, workflows) must still be keyed off the
    original repo root rather than the ephemeral worktree path, otherwise each
    worktree would get its own isolated storage namespace.

    All symlinks are fully resolved so that different string representations of
    the same physical directory (e.g. ``/Users/…`` vs ``/private/Users/…`` on
    macOS) always produce the same canonical path — and therefore the same
    project ID hash.
    """
    try:
        resolved = Path(os.path.realpath(project_path))
    except Exception:
        resolved = project_path

    parts = resolved.parts
    for idx in range(len(parts) - 1):
        if parts[idx] == ".pixl" and parts[idx + 1] == "worktrees":
            # /<repo>/.pixl/worktrees/<session_id>/... -> /<repo>
            return Path(*parts[:idx])
    return resolved


def get_global_pixl_dir() -> Path:
    """Get global pixl directory (default: ~/.pixl/)."""
    override = os.getenv("PIXL_GLOBAL_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".pixl"


def get_project_name(project_path: Path) -> str:
    """Resolve project name for storage namespaces."""
    project_path = canonical_project_root(project_path)
    override = os.getenv("PIXL_PROJECT_NAME")
    if override:
        return _slugify(override)
    return _slugify(project_path.name)


def get_project_id(project_path: Path) -> str:
    """Create a stable, collision-resistant project identifier."""
    project_path = canonical_project_root(project_path)
    name = get_project_name(project_path)
    digest = hashlib.sha1(str(project_path).encode("utf-8")).hexdigest()[:8]
    return f"{name}-{digest}"


def get_project_workspace_dir(project_path: Path) -> Path:
    """Get external workspace root for a project."""
    project_path = canonical_project_root(project_path)
    return get_global_pixl_dir() / "projects" / get_project_id(project_path)


def get_pixl_dir(project_path: Path) -> Path:
    """Get pixl directory for this project.

    Prefers the embedded ``{project}/.pixl`` directory if it exists,
    otherwise falls back to the standalone ``~/.pixl/projects/<project-id>/``.
    If *project_path* is already inside the global projects directory,
    returns it directly to avoid double-hashing.
    """
    project_path = canonical_project_root(project_path)

    # Prefer embedded .pixl if it exists
    embedded = project_path / ".pixl"
    if embedded.is_dir():
        return embedded

    global_projects = get_global_pixl_dir() / "projects"
    try:
        project_path.resolve().relative_to(global_projects.resolve())
        # Already inside ~/.pixl/projects/ — return as-is
        return project_path
    except ValueError:
        pass
    return get_project_workspace_dir(project_path)


def get_sessions_dir(project_path: Path) -> Path:
    return get_pixl_dir(project_path) / "sessions"


def get_workflows_dir(project_path: Path) -> Path:
    return get_pixl_dir(project_path) / "workflows"


def get_prompts_dir(project_path: Path) -> Path:
    return get_pixl_dir(project_path) / "prompts"
