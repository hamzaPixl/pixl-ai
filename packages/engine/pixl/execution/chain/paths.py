"""Path resolution for chain execution — handles standalone vs embedded storage."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB


def resolve_project_root(db: PixlDB) -> Path:
    """Resolve the actual project root (git repo) from the DB context.

    In standalone storage mode, db.project_path is ~/.pixl/projects/<id>/
    which is NOT a git repo. The actual project root is stored in the
    project registry under 'project_root'.
    """
    from pixl.projects.registry import get_project

    project_id = db.project_path.name
    info = get_project(project_id)
    if info and info.get("project_root"):
        return Path(info["project_root"])
    return db.project_path


def resolve_storage_root(db: PixlDB) -> Path:
    """Resolve the storage root (DB/sessions/snapshots) from the DB context.

    In standalone mode this is ``~/.pixl/projects/<id>/`` (the registry's
    ``storage_dir``).  In embedded mode it falls back to ``db.project_path``
    which already points at the repo root containing ``.pixl/``.

    This MUST be used for WorkflowStore, WorkflowSessionStore,
    get_sessions_dir, and any session/snapshot file access.
    ``resolve_project_root`` MUST be used for git operations only.
    """
    from pixl.projects.registry import get_project

    project_id = db.project_path.name
    info = get_project(project_id)
    if info and info.get("storage_dir"):
        return Path(info["storage_dir"])
    return db.project_path
