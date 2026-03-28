"""Workspace project database operations."""

from __future__ import annotations

from pixl_api.db._connection import get_connection


def list_workspace_projects(ws_id: str) -> list[dict]:
    """List all projects linked to a workspace."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM workspace_projects WHERE workspace_id = ? ORDER BY linked_at",
        (ws_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def link_project(ws_id: str, project_id: str) -> dict:
    """Link a project to a workspace (idempotent)."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO workspace_projects (workspace_id, project_id) VALUES (?, ?)",
        (ws_id, project_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM workspace_projects WHERE workspace_id = ? AND project_id = ?",
        (ws_id, project_id),
    ).fetchone()
    conn.close()
    return dict(row)
