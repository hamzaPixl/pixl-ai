"""Workspace database operations."""

from __future__ import annotations

import uuid

from pixl_api.db._connection import get_connection


def get_default_workspace(user_id: str) -> dict | None:
    """Return the first workspace owned by *user_id*, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM workspaces WHERE owner_id = ? ORDER BY created_at LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def ensure_workspace(user_id: str, name: str = "Default") -> dict:
    """Return the user's workspace, creating one if none exists.

    Also ensures the owner is an admin member of the workspace.
    """
    ws = get_default_workspace(user_id)
    if ws:
        # Ensure membership exists (migration path for pre-existing workspaces)
        _ensure_member(ws["id"], user_id, "admin")
        return ws
    wid = uuid.uuid4().hex
    conn = get_connection()
    conn.execute(
        "INSERT INTO workspaces (id, name, owner_id) VALUES (?, ?, ?)",
        (wid, name, user_id),
    )
    conn.execute(
        "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (?, ?, ?)",
        (wid, user_id, "admin"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM workspaces WHERE id = ?", (wid,)).fetchone()
    conn.close()
    return dict(row)


def _ensure_member(ws_id: str, user_id: str, role: str) -> None:
    """Insert a workspace member if not already present."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO workspace_members (workspace_id, user_id, role) VALUES (?, ?, ?)",
        (ws_id, user_id, role),
    )
    conn.commit()
    conn.close()


def create_workspace(name: str, owner_id: str) -> dict:
    """Create a workspace and auto-add the owner as an admin member."""
    wid = uuid.uuid4().hex
    conn = get_connection()
    conn.execute(
        "INSERT INTO workspaces (id, name, owner_id) VALUES (?, ?, ?)",
        (wid, name, owner_id),
    )
    conn.execute(
        "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (?, ?, ?)",
        (wid, owner_id, "admin"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM workspaces WHERE id = ?", (wid,)).fetchone()
    conn.close()
    return dict(row)


def get_workspace(ws_id: str) -> dict | None:
    """Get a workspace by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM workspaces WHERE id = ?", (ws_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_workspaces(user_id: str) -> list[dict]:
    """List all workspaces the user is a member of (or owns)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT w.* FROM workspaces w "
        "LEFT JOIN workspace_members wm ON w.id = wm.workspace_id "
        "WHERE w.owner_id = ? OR wm.user_id = ? "
        "ORDER BY w.created_at",
        (user_id, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_workspace(ws_id: str) -> bool:
    """Delete a workspace."""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM workspaces WHERE id = ?", (ws_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def list_workspace_members(ws_id: str) -> list[dict]:
    """List all members of a workspace with user info."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT wm.workspace_id, wm.user_id, wm.role, wm.joined_at, "
        "u.email, u.first_name, u.last_name "
        "FROM workspace_members wm "
        "JOIN users u ON wm.user_id = u.id "
        "WHERE wm.workspace_id = ? "
        "ORDER BY wm.joined_at",
        (ws_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_workspace_member(ws_id: str, user_id: str, role: str = "member") -> dict:
    """Add a member to a workspace."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO workspace_members (workspace_id, user_id, role) VALUES (?, ?, ?)",
        (ws_id, user_id, role),
    )
    conn.commit()
    row = conn.execute(
        "SELECT wm.workspace_id, wm.user_id, wm.role, wm.joined_at, "
        "u.email, u.first_name, u.last_name "
        "FROM workspace_members wm "
        "JOIN users u ON wm.user_id = u.id "
        "WHERE wm.workspace_id = ? AND wm.user_id = ?",
        (ws_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row)


def change_member_role(ws_id: str, user_id: str, role: str) -> bool:
    """Change a member's role in a workspace."""
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE workspace_members SET role = ? WHERE workspace_id = ? AND user_id = ?",
        (role, ws_id, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def remove_workspace_member(ws_id: str, user_id: str) -> bool:
    """Remove a member from a workspace."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
        (ws_id, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
