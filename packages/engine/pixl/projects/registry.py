"""Project registry — centralized index + global DB storage.

Projects are tracked in ``~/.pixl/projects.json`` (lightweight index).
Project data (DB) lives at ``~/.pixl/projects/<id>/``.
Local context (workflows, sessions) lives at ``{project}/.pixl/``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pixl.paths import get_global_pixl_dir, get_project_workspace_dir

_INDEX_FILE = "projects.json"


# ── Index operations ─────────────────────────────────────────────────────


def _index_path(global_dir: Path | None = None) -> Path:
    return (global_dir or get_global_pixl_dir()) / _INDEX_FILE


def _load_index(global_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the project index. Returns {project_id: {name, root}}."""
    path = _index_path(global_dir)
    if not path.exists():
        return {}
    try:
        result: dict[str, dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        return result
    except (json.JSONDecodeError, OSError):
        return {}


def _save_index(index: dict[str, dict[str, Any]], global_dir: Path | None = None) -> None:
    path = _index_path(global_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")


def register_project(
    project_id: str,
    name: str,
    root: str | None = None,
    global_dir: Path | None = None,
) -> None:
    """Add or update a project in the index. Idempotent."""
    index = _load_index(global_dir)
    index[project_id] = {"name": name, "root": root}
    _save_index(index, global_dir)


def unregister_project(project_id: str, global_dir: Path | None = None) -> None:
    """Remove a project from the index."""
    index = _load_index(global_dir)
    index.pop(project_id, None)
    _save_index(index, global_dir)


# ── Project info ─────────────────────────────────────────────────────────


def _project_info_from_dir(project_dir: Path) -> dict[str, Any] | None:
    """Build project info from a global workspace directory."""
    if not project_dir.is_dir():
        return None

    config_path = project_dir / "config.json"
    config: dict[str, Any] = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    db_path = project_dir / "pixl.db"

    info: dict[str, Any] = {
        "project_id": project_dir.name,
        "project_name": config.get("project_name") or config.get("name") or project_dir.name,
        "project_root": config.get("project_root") or config.get("root"),
        "storage_dir": str(project_dir),
        "db_path": str(db_path) if db_path.exists() else None,
    }

    try:
        info["last_used_at"] = db_path.stat().st_mtime if db_path.exists() else None
    except OSError:
        info["last_used_at"] = None

    return info


def _project_info_from_index(
    project_id: str, entry: dict[str, Any], global_dir: Path | None = None
) -> dict[str, Any]:
    """Build project info from an index entry."""
    base_dir = global_dir or get_global_pixl_dir()
    project_dir = base_dir / "projects" / project_id
    db_path = project_dir / "pixl.db"

    info: dict[str, Any] = {
        "project_id": project_id,
        "project_name": entry.get("name", project_id),
        "project_root": entry.get("root"),
        "storage_dir": str(project_dir),
        "db_path": str(db_path) if db_path.exists() else None,
    }

    try:
        info["last_used_at"] = db_path.stat().st_mtime if db_path.exists() else None
    except OSError:
        info["last_used_at"] = None

    return info


# ── Public API ───────────────────────────────────────────────────────────


def list_projects(global_dir: Path | None = None) -> list[dict[str, Any]]:
    """List all known projects.

    Merges the ``projects.json`` index with any directories found in
    ``~/.pixl/projects/`` (backward compatibility).
    """
    base_dir = global_dir or get_global_pixl_dir()
    seen: set[str] = set()
    projects: list[dict[str, Any]] = []

    # 1. Read index (primary source)
    index = _load_index(global_dir)
    for pid, entry in sorted(index.items()):
        projects.append(_project_info_from_index(pid, entry, global_dir))
        seen.add(pid)

    # 2. Scan directories for unregistered projects (backward compat)
    projects_dir = base_dir / "projects"
    if projects_dir.exists():
        for project_dir in sorted(projects_dir.iterdir()):
            if project_dir.name in seen:
                continue
            info = _project_info_from_dir(project_dir)
            if info:
                projects.append(info)
                # Auto-register in index for future runs
                register_project(
                    project_dir.name,
                    info.get("project_name", project_dir.name),
                    info.get("project_root"),
                    global_dir,
                )

    return projects


def get_project(project_id: str, global_dir: Path | None = None) -> dict[str, Any] | None:
    """Get project info by project_id."""
    # Check index first
    index = _load_index(global_dir)
    if project_id in index:
        return _project_info_from_index(project_id, index[project_id], global_dir)

    # Fallback to directory scan
    base_dir = global_dir or get_global_pixl_dir()
    project_dir = base_dir / "projects" / project_id
    return _project_info_from_dir(project_dir)


def create_project(
    name: str,
    description: str,
    project_root: str | None = None,
    global_dir: Path | None = None,
    github_clone_url: str | None = None,
) -> dict[str, Any]:
    """Create a new project in the global workspace.

    Creates the directory structure, writes config, and registers in the index.
    """
    import hashlib as _hashlib
    import re as _re

    base_dir = global_dir or get_global_pixl_dir()

    if project_root:
        from pixl.paths import get_project_id as _get_project_id

        project_id = _get_project_id(Path(project_root))
    else:
        slug = _re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-").replace("_", "-"))
        slug = _re.sub(r"-+", "-", slug).strip("-") or "project"
        digest = _hashlib.sha1(f"{slug}-{name}".encode()).hexdigest()[:8]
        project_id = f"{slug}-{digest}"

    project_dir = base_dir / "projects" / project_id
    if project_dir.exists():
        raise ValueError(f"Project directory already exists: {project_id}")

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "sessions").mkdir(exist_ok=True)

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

    # Register in index
    register_project(project_id, name, project_root, global_dir)

    info = _project_info_from_dir(project_dir)
    if info is None:
        raise RuntimeError(f"Failed to read back created project: {project_id}")

    return info


def ensure_project_config(project_path: Path) -> None:
    """Ensure project is registered in the global index.

    Called from CLI ``project init`` to register an existing directory.
    """
    from pixl.paths import get_project_id as _get_project_id
    from pixl.paths import get_project_name as _get_project_name

    project_id = _get_project_id(project_path)
    project_name = _get_project_name(project_path)

    # Register in index
    register_project(project_id, project_name, str(project_path.resolve()))

    # Ensure global DB dir exists
    workspace_dir = get_project_workspace_dir(project_path)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Write config.json in global dir
    config_path = workspace_dir / "config.json"
    if not config_path.exists():
        config_path.write_text(
            json.dumps(
                {
                    "project_name": project_name,
                    "project_root": str(project_path.resolve()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def delete_project(
    project_id: str,
    global_dir: Path | None = None,
) -> bool:
    """Delete a project completely.

    Removes from index, removes global workspace dir, removes embedded .pixl/.
    """
    base_dir = global_dir or get_global_pixl_dir()
    project_dir = base_dir / "projects" / project_id

    # Read project root before deleting
    project_root: str | None = None
    index = _load_index(global_dir)
    if project_id in index:
        project_root = index[project_id].get("root")
    elif project_dir.is_dir():
        config_path = project_dir / "config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                project_root = config.get("project_root") or config.get("root")
            except (json.JSONDecodeError, OSError):
                pass
    else:
        return False

    # 1. Remove from index
    unregister_project(project_id, global_dir)

    # 2. Remove global workspace dir
    if project_dir.is_dir():
        shutil.rmtree(project_dir)

    # 3. Remove embedded .pixl/ in project root
    if project_root:
        embedded = Path(project_root) / ".pixl"
        if embedded.is_dir():
            shutil.rmtree(embedded)

    return True
