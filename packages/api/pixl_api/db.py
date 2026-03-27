"""Minimal single-tenant user database backed by SQLite."""

from __future__ import annotations

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
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES users(id),
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
    conn.close()


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
        "SELECT id, email, first_name, last_name, created_at FROM users WHERE id = ?",
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
    """Return the user's workspace, creating one if none exists."""
    ws = get_default_workspace(user_id)
    if ws:
        return ws
    wid = uuid.uuid4().hex
    conn = get_connection()
    conn.execute(
        "INSERT INTO workspaces (id, name, owner_id) VALUES (?, ?, ?)",
        (wid, name, user_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM workspaces WHERE id = ?", (wid,)).fetchone()
    conn.close()
    return dict(row)
