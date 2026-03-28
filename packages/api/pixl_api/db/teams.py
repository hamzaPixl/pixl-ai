"""Team database operations."""

from __future__ import annotations

import uuid

from pixl_api.db._connection import get_connection


def create_team(
    ws_id: str,
    name: str,
    description: str = "",
    color: str = "",
) -> dict:
    """Create a team in a workspace."""
    tid = uuid.uuid4().hex
    conn = get_connection()
    conn.execute(
        "INSERT INTO teams (id, workspace_id, name, description, color) VALUES (?, ?, ?, ?, ?)",
        (tid, ws_id, name, description, color),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM teams WHERE id = ?", (tid,)).fetchone()
    conn.close()
    return dict(row)


def list_teams(ws_id: str) -> list[dict]:
    """List all teams in a workspace."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM teams WHERE workspace_id = ? ORDER BY created_at",
        (ws_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_team(
    ws_id: str,
    team_id: str,
    name: str | None = None,
    description: str | None = None,
    color: str | None = None,
) -> dict | None:
    """Update a team's fields. Returns updated team or None if not found."""
    fields: dict[str, str] = {}
    if name is not None:
        fields["name"] = name
    if description is not None:
        fields["description"] = description
    if color is not None:
        fields["color"] = color
    if not fields:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM teams WHERE id = ? AND workspace_id = ?", (team_id, ws_id)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [team_id, ws_id]
    conn = get_connection()
    cursor = conn.execute(
        f"UPDATE teams SET {set_clause} WHERE id = ? AND workspace_id = ?", values
    )
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        return None
    row = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_team(ws_id: str, team_id: str) -> bool:
    """Delete a team from a workspace."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM teams WHERE id = ? AND workspace_id = ?",
        (team_id, ws_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def list_team_members(ws_id: str, team_id: str) -> list[dict]:
    """List all members of a team."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tm.team_id, tm.user_id, u.email, u.first_name, u.last_name "
        "FROM team_members tm "
        "JOIN users u ON tm.user_id = u.id "
        "JOIN teams t ON tm.team_id = t.id "
        "WHERE tm.team_id = ? AND t.workspace_id = ? "
        "ORDER BY u.email",
        (team_id, ws_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_team_member(ws_id: str, team_id: str, user_id: str) -> dict:
    """Add a user to a team."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO team_members (team_id, user_id) VALUES (?, ?)",
        (team_id, user_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT tm.team_id, tm.user_id, u.email, u.first_name, u.last_name "
        "FROM team_members tm "
        "JOIN users u ON tm.user_id = u.id "
        "WHERE tm.team_id = ? AND tm.user_id = ?",
        (team_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row)


def remove_team_member(ws_id: str, team_id: str, user_id: str) -> bool:
    """Remove a user from a team."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM team_members WHERE team_id = ? AND user_id = ? "
        "AND team_id IN (SELECT id FROM teams WHERE workspace_id = ?)",
        (team_id, user_id, ws_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
