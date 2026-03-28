"""Invitation database operations."""

from __future__ import annotations

import uuid

from pixl_api.db._connection import get_connection


def create_invitation(ws_id: str, email: str, role: str = "member") -> dict:
    """Create a workspace invitation."""
    inv_id = uuid.uuid4().hex
    conn = get_connection()
    conn.execute(
        "INSERT INTO invitations (id, workspace_id, email, role) VALUES (?, ?, ?, ?)",
        (inv_id, ws_id, email, role),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM invitations WHERE id = ?", (inv_id,)).fetchone()
    conn.close()
    return dict(row)


def list_invitations(ws_id: str) -> list[dict]:
    """List pending invitations for a workspace."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM invitations"
        " WHERE workspace_id = ? AND status = 'pending'"
        " ORDER BY created_at",
        (ws_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def revoke_invitation(ws_id: str, inv_id: str) -> bool:
    """Delete an invitation."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM invitations WHERE id = ? AND workspace_id = ?",
        (inv_id, ws_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
