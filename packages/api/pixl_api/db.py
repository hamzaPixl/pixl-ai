"""Minimal single-tenant user database backed by SQLite."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from pathlib import Path

DB_PATH: Path = Path.home() / ".pixl" / "api.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    onboarding_completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',
    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    color TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (team_id, user_id)
);

CREATE TABLE IF NOT EXISTS invitations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workspace_projects (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL,
    linked_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (workspace_id, project_id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    prefix TEXT NOT NULL,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    rate_limit_rpm INTEGER NOT NULL DEFAULT 60,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection() -> sqlite3.Connection:
    """Return a new connection to the API database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.executescript(_SCHEMA)
    # Migrate: add onboarding_completed if missing
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "onboarding_completed" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Workspace Members
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Team Members
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Workspace Projects
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


def create_api_key(
    user_id: str,
    name: str,
    scopes: list[str] | None = None,
    rate_limit_rpm: int = 60,
) -> dict:
    """Create an API key. Returns the raw key only once.

    The raw key is ``pk_`` + 32 random hex chars.
    Only the SHA-256 hash is stored in the database.
    """
    if scopes is None:
        scopes = []
    key_id = uuid.uuid4().hex
    raw_key = "pk_" + secrets.token_hex(16)
    prefix = raw_key[:11]  # "pk_" + 8 hex chars
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    conn = get_connection()
    conn.execute(
        "INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes_json, rate_limit_rpm) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (key_id, user_id, name, key_hash, prefix, json.dumps(scopes), rate_limit_rpm),
    )
    conn.commit()
    conn.close()
    return {
        "id": key_id,
        "key": raw_key,
        "name": name,
        "prefix": prefix,
        "scopes": scopes,
        "rate_limit_rpm": rate_limit_rpm,
    }


def list_api_keys(user_id: str) -> list[dict]:
    """List active API keys for a user (without key hashes)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, prefix, scopes_json, rate_limit_rpm, is_active, created_at "
        "FROM api_keys WHERE user_id = ? AND is_active = 1 ORDER BY created_at",
        (user_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["scopes"] = json.loads(d.pop("scopes_json"))
        d["is_active"] = bool(d["is_active"])
        result.append(d)
    return result


def revoke_api_key(key_id: str, user_id: str) -> bool:
    """Revoke (soft-delete) an API key. Only the owning user can revoke."""
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE api_keys SET is_active = 0 WHERE id = ? AND user_id = ? AND is_active = 1",
        (key_id, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
