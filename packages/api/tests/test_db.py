"""Tests for the user database module."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pixl_api.db import (
    create_user,
    ensure_workspace,
    get_connection,
    get_default_workspace,
    get_user_by_email,
    get_user_by_id,
    init_db,
)


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect DB_PATH to a temp directory for every test."""
    db_path = tmp_path / "api.db"
    monkeypatch.setattr("pixl_api.db.DB_PATH", db_path)
    init_db()


# --- init_db ---


def test_init_db_creates_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr("pixl_api.db.DB_PATH", db_path)
    init_db()

    conn = get_connection()
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "users" in tables
    assert "workspaces" in tables


def test_init_db_is_idempotent() -> None:
    # Calling init_db twice should not raise.
    init_db()


def test_wal_mode_enabled() -> None:
    conn = get_connection()
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


# --- create_user / get_user_by_email / get_user_by_id ---


def test_create_user_returns_user_dict() -> None:
    user = create_user("alice@example.com", "hashed_pw", "Alice", "Smith")
    assert user["email"] == "alice@example.com"
    assert user["first_name"] == "Alice"
    assert user["last_name"] == "Smith"
    assert "id" in user
    assert "created_at" in user
    assert "password_hash" not in user


def test_create_user_duplicate_email_raises() -> None:
    create_user("bob@example.com", "hash1")
    with pytest.raises(sqlite3.IntegrityError):
        create_user("bob@example.com", "hash2")


def test_get_user_by_email_found() -> None:
    create_user("carol@example.com", "hash")
    user = get_user_by_email("carol@example.com")
    assert user is not None
    assert user["email"] == "carol@example.com"
    assert user["password_hash"] == "hash"


def test_get_user_by_email_not_found() -> None:
    assert get_user_by_email("nobody@example.com") is None


def test_get_user_by_id_found() -> None:
    created = create_user("dave@example.com", "hash")
    user = get_user_by_id(created["id"])
    assert user is not None
    assert user["email"] == "dave@example.com"


def test_get_user_by_id_not_found() -> None:
    assert get_user_by_id("nonexistent") is None


def test_create_user_default_names() -> None:
    user = create_user("noname@example.com", "hash")
    assert user["first_name"] == ""
    assert user["last_name"] == ""


# --- workspaces ---


def test_ensure_workspace_creates_workspace() -> None:
    user = create_user("ws@example.com", "hash")
    ws = ensure_workspace(user["id"])
    assert ws["name"] == "Default"
    assert ws["owner_id"] == user["id"]
    assert "id" in ws
    assert "created_at" in ws


def test_ensure_workspace_idempotent() -> None:
    user = create_user("ws2@example.com", "hash")
    ws1 = ensure_workspace(user["id"])
    ws2 = ensure_workspace(user["id"])
    assert ws1["id"] == ws2["id"]


def test_get_default_workspace_returns_none_before_creation() -> None:
    user = create_user("ws3@example.com", "hash")
    assert get_default_workspace(user["id"]) is None


def test_get_default_workspace_returns_workspace_after_ensure() -> None:
    user = create_user("ws4@example.com", "hash")
    ensure_workspace(user["id"])
    ws = get_default_workspace(user["id"])
    assert ws is not None
    assert ws["owner_id"] == user["id"]


def test_ensure_workspace_custom_name() -> None:
    user = create_user("ws5@example.com", "hash")
    ws = ensure_workspace(user["id"], name="My Project")
    assert ws["name"] == "My Project"
