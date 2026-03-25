"""Helpers for resolving Pixl storage paths.

DB always lives at ``~/.pixl/projects/<project-id>/pixl.db`` (global).
Local context (workflows, sessions) lives at ``{project}/.pixl/`` (embedded).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path

# Test override — set via monkeypatch in conftest.py
_global_pixl_dir_override: Path | None = None


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
    if _global_pixl_dir_override is not None:
        return _global_pixl_dir_override
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


def get_db_dir(project_path: Path) -> Path:
    """Get the global DB directory for this project.

    Always returns ``~/.pixl/projects/<project-id>/``.
    Auto-migrates embedded ``pixl.db`` to global on first access.
    """
    project_path = canonical_project_root(project_path)
    global_dir = get_project_workspace_dir(project_path)

    # Auto-migrate: if embedded DB exists but global doesn't, move it
    embedded = project_path / ".pixl"
    embedded_db = embedded / "pixl.db"
    global_db = global_dir / "pixl.db"
    if embedded_db.exists() and not global_db.exists():
        global_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(embedded_db), str(global_db))
        for suffix in ["-wal", "-shm"]:
            wal = embedded / f"pixl.db{suffix}"
            if wal.exists():
                shutil.move(str(wal), str(global_dir / f"pixl.db{suffix}"))

    return global_dir


def get_context_dir(project_path: Path) -> Path:
    """Get the local context directory for this project.

    Returns ``{project}/.pixl/`` — used for workflows, sessions, local overrides.
    Does NOT contain the DB (that lives in ``get_db_dir()``).
    """
    return canonical_project_root(project_path) / ".pixl"


def get_pixl_dir(project_path: Path) -> Path:
    """Get pixl directory for this project.

    .. deprecated:: 9.1.0
        Use ``get_db_dir()`` for DB access or ``get_context_dir()`` for local context.

    Returns the global DB directory (``~/.pixl/projects/<id>/``).
    For standalone projects already inside ``~/.pixl/projects/``, returns as-is.
    """
    project_path = canonical_project_root(project_path)

    global_projects = get_global_pixl_dir() / "projects"
    try:
        project_path.resolve().relative_to(global_projects.resolve())
        # Already inside ~/.pixl/projects/ — return as-is
        return project_path
    except ValueError:
        pass
    return get_db_dir(project_path)


def get_sessions_dir(project_path: Path) -> Path:
    return get_context_dir(project_path) / "sessions"


def get_workflows_dir(project_path: Path) -> Path:
    return get_context_dir(project_path) / "workflows"


def get_prompts_dir(project_path: Path) -> Path:
    return get_context_dir(project_path) / "prompts"
