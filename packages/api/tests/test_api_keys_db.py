"""Tests for API key database functions."""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl_api.db import (
    create_api_key,
    create_user,
    init_db,
    list_api_keys,
    revoke_api_key,
)


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect DB_PATH to a temp directory for every test."""
    db_path = tmp_path / "api.db"
    monkeypatch.setattr("pixl_api.db._connection.DB_PATH", db_path)
    init_db()


def test_create_api_key_returns_raw_key() -> None:
    user = create_user("keyuser@example.com", "hash")
    result = create_api_key(user["id"], "My Key", ["read", "write"], 120)
    assert result["name"] == "My Key"
    assert result["key"].startswith("pk_")
    assert len(result["key"]) == 35  # "pk_" + 32 hex chars
    assert result["prefix"] == result["key"][:11]  # "pk_" + 8 hex chars
    assert result["scopes"] == ["read", "write"]
    assert result["rate_limit_rpm"] == 120
    assert "id" in result


def test_list_api_keys_does_not_include_hash() -> None:
    user = create_user("listkey@example.com", "hash")
    create_api_key(user["id"], "Key 1", ["read"], 60)
    create_api_key(user["id"], "Key 2", ["write"], 100)
    keys = list_api_keys(user["id"])
    assert len(keys) == 2
    for key in keys:
        assert "key_hash" not in key
        assert "key" not in key
        assert "name" in key
        assert "prefix" in key
        assert "scopes" in key
        assert "is_active" in key


def test_list_api_keys_only_returns_active() -> None:
    user = create_user("activekey@example.com", "hash")
    result = create_api_key(user["id"], "Active Key", [], 60)
    create_api_key(user["id"], "Other Key", [], 60)
    revoke_api_key(result["id"], user["id"])
    keys = list_api_keys(user["id"])
    assert len(keys) == 1
    assert keys[0]["name"] == "Other Key"


def test_revoke_api_key() -> None:
    user = create_user("revokekey@example.com", "hash")
    result = create_api_key(user["id"], "To Revoke", [], 60)
    assert revoke_api_key(result["id"], user["id"])
    keys = list_api_keys(user["id"])
    assert len(keys) == 0


def test_revoke_api_key_wrong_user() -> None:
    user1 = create_user("keyowner@example.com", "hash")
    user2 = create_user("keyother@example.com", "hash")
    result = create_api_key(user1["id"], "Owner Key", [], 60)
    assert not revoke_api_key(result["id"], user2["id"])
    keys = list_api_keys(user1["id"])
    assert len(keys) == 1


def test_create_api_key_default_scopes_and_rate_limit() -> None:
    user = create_user("defaultkey@example.com", "hash")
    result = create_api_key(user["id"], "Default Key")
    assert result["scopes"] == []
    assert result["rate_limit_rpm"] == 60
