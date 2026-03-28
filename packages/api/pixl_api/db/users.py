"""User database operations."""

from __future__ import annotations

import uuid

from pixl_api.db._connection import get_connection


def create_user(
    email: str,
    password_hash: str,
    first_name: str = "",
    last_name: str = "",
) -> dict:
    """Create a user and return a safe dict (no password_hash)."""
    uid = uuid.uuid4().hex
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, first_name, last_name) "
        "VALUES (?, ?, ?, ?, ?)",
        (uid, email, password_hash, first_name, last_name),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, email, first_name, last_name,"
        " onboarding_completed, created_at FROM users WHERE id = ?",
        (uid,),
    ).fetchone()
    conn.close()
    return dict(row)


def get_user_by_email(email: str) -> dict | None:
    """Look up a user by email. Returns full row (including password_hash) or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    """Look up a user by ID. Returns full row (including password_hash) or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(user_id: str, **fields: str) -> dict | None:
    """Update user fields and return the updated user (without password_hash)."""
    if not fields:
        return get_user_by_id(user_id)
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    conn = get_connection()
    conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    row = conn.execute(
        "SELECT id, email, first_name, last_name,"
        " onboarding_completed, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def complete_onboarding(user_id: str) -> bool:
    """Mark onboarding as complete for a user."""
    conn = get_connection()
    cursor = conn.execute("UPDATE users SET onboarding_completed = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def update_password(user_id: str, new_hash: str) -> bool:
    """Update a user's password hash."""
    conn = get_connection()
    cursor = conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def delete_user(user_id: str) -> bool:
    """Delete a user and their workspaces."""
    conn = get_connection()
    conn.execute("DELETE FROM workspaces WHERE owner_id = ?", (user_id,))
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
