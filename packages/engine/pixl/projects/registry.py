"""Project registry helpers for multi-project setups."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pixl.paths import get_global_pixl_dir


def _load_config(project_dir: Path) -> dict[str, Any]:
    config_path = project_dir / "config.json"
    if not config_path.exists():
        return {}
    try:
        result: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        return result
    except (json.JSONDecodeError, OSError):
        return {}


def _project_info(project_dir: Path) -> dict[str, Any] | None:
    if not project_dir.is_dir():
        return None

    config = _load_config(project_dir)
    db_path = project_dir / "pixl.db"

    info: dict[str, Any] = {
        "project_id": project_dir.name,
        "project_name": config.get("project_name") or project_dir.name,
        "project_root": config.get("project_root") or config.get("project_path"),
        "storage_dir": str(project_dir),
        "db_path": str(db_path) if db_path.exists() else None,
        "storage_mode": config.get("storage_mode"),
    }

    try:
        info["last_used_at"] = db_path.stat().st_mtime if db_path.exists() else None
    except OSError:
        info["last_used_at"] = None

    return info


def list_projects(global_dir: Path | None = None) -> list[dict[str, Any]]:
    """List all known projects from the global pixl workspace."""
    base_dir = global_dir or get_global_pixl_dir()
    projects_dir = base_dir / "projects"
    if not projects_dir.exists():
        return []

    projects: list[dict[str, Any]] = []
    for project_dir in sorted(projects_dir.iterdir()):
        info = _project_info(project_dir)
        if info:
            projects.append(info)

    return projects


def get_project(project_id: str, global_dir: Path | None = None) -> dict[str, Any] | None:
    """Get project info by project_id."""
    base_dir = global_dir or get_global_pixl_dir()
    project_dir = base_dir / "projects" / project_id
    return _project_info(project_dir)


def create_project(
    name: str,
    description: str,
    project_root: str | None = None,
    global_dir: Path | None = None,
    github_clone_url: str | None = None,
) -> dict[str, Any]:
    """Create a new project in the global pixl workspace.

    Creates the directory structure and writes initial config.json.
    Returns project info dict (same shape as _project_info).
    """
    import hashlib
    import re

    base_dir = global_dir or get_global_pixl_dir()
    projects_dir = base_dir / "projects"

    if project_root:
        # Match paths.py:get_project_id() — hash from resolved path
        from pixl.paths import get_project_id

        project_id = get_project_id(Path(project_root))
    else:
        # Fallback: name-based hash for projects without a filesystem path
        slug = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-").replace("_", "-"))
        slug = re.sub(r"-+", "-", slug).strip("-") or "project"
        digest = hashlib.sha1(f"{slug}-{name}".encode()).hexdigest()[:8]
        project_id = f"{slug}-{digest}"

    project_dir = projects_dir / project_id
    if project_dir.exists():
        raise ValueError(f"Project directory already exists: {project_id}")

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "sessions").mkdir(exist_ok=True)

    # Write config.json
    config: dict[str, Any] = {
        "project_name": name,
        "description": description,
        "storage_mode": "standalone",
    }
    if github_clone_url and project_root:
        from pixl.execution.git_utils import git_clone

        ok, err = git_clone(github_clone_url, Path(project_root))
        if not ok:
            raise RuntimeError(f"Failed to clone GitHub repo: {err}")
        config["github_repo"] = github_clone_url
    elif project_root:
        Path(project_root).mkdir(parents=True, exist_ok=True)

    if project_root:
        config["project_root"] = project_root

    config_path = project_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    info = _project_info(project_dir)
    if info is None:
        raise RuntimeError(f"Failed to read back created project: {project_id}")

    return info


def ensure_project_config(project_path: Path) -> None:
    """Backfill ``project_root`` into config.json if missing.

    Called from CLI commands so that projects created via the CLI
    (which only store data under ``~/.pixl/projects/<id>/``) also
    record the original filesystem root, aligning them with
    API-created projects.
    """
    from pixl.paths import get_pixl_dir

    pixl_dir = get_pixl_dir(project_path)
    config_path = pixl_dir / "config.json"

    config: dict[str, Any] = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if config.get("project_root"):
        return

    # Only backfill for real filesystem projects (not standalone-only ones)
    resolved = project_path.resolve()
    global_projects = Path.home() / ".pixl" / "projects"
    try:
        resolved.relative_to(global_projects)
        # Already inside ~/.pixl/projects/ — no external root to record
        return
    except ValueError:
        pass

    config["project_root"] = str(resolved)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def delete_project(
    project_id: str,
    global_dir: Path | None = None,
) -> bool:
    """Delete a project by removing its directory from the global workspace.

    Returns True if the project was deleted, False if it didn't exist.
    """
    base_dir = global_dir or get_global_pixl_dir()
    project_dir = base_dir / "projects" / project_id

    if not project_dir.is_dir():
        return False

    shutil.rmtree(project_dir)
    return True
