"""Tests for API key route endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pixl_api.app import create_app
from pixl_api.db import create_user, ensure_workspace, init_db
from pixl_api.foundation.auth.core import encode_jwt
from pixl_api.foundation.auth.secret import get_jwt_secret


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect DB_PATH to a temp directory for every test."""
    db_path = tmp_path / "api.db"
    monkeypatch.setattr("pixl_api.db.DB_PATH", db_path)
    init_db()


@pytest.fixture()
def user_and_token() -> dict[str, Any]:
    """Create a test user with workspace and return user dict + JWT token."""
    user = create_user("test@example.com", "hashed_pw", "Test", "User")
    ensure_workspace(user["id"])
    token = encode_jwt({"sub": user["id"], "email": user["email"]}, get_jwt_secret())
    return {"user": user, "token": token}


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def auth_headers(user_and_token: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_and_token['token']}"}


# --- GET /keys ---


def test_list_keys_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/keys", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


# --- POST /keys ---


def test_create_api_key(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/keys",
        headers=auth_headers,
        json={"name": "Test Key", "scopes": ["read"], "rate_limit_rpm": 100},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "key" in data
    assert data["key"].startswith("pk_")
    assert data["name"] == "Test Key"
    assert data["scopes"] == ["read"]
    assert data["rate_limit_rpm"] == 100
    assert "id" in data
    assert "prefix" in data


def test_create_api_key_minimal(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/keys",
        headers=auth_headers,
        json={"name": "Minimal Key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scopes"] == []
    assert data["rate_limit_rpm"] == 60


# --- GET /keys after creation ---


def test_list_keys_after_creation(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post(
        "/api/keys",
        headers=auth_headers,
        json={"name": "Listed Key"},
    )
    resp = client.get("/api/keys", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    key_out = data[0]
    assert key_out["name"] == "Listed Key"
    assert key_out["is_active"] is True
    assert "key" not in key_out
    assert "key_hash" not in key_out


# --- DELETE /keys/{id} ---


def test_revoke_api_key(client: TestClient, auth_headers: dict[str, str]) -> None:
    create_resp = client.post(
        "/api/keys",
        headers=auth_headers,
        json={"name": "To Revoke"},
    )
    key_id = create_resp.json()["id"]
    resp = client.delete(f"/api/keys/{key_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert "message" in resp.json()

    # Verify it's gone from the list
    list_resp = client.get("/api/keys", headers=auth_headers)
    assert len(list_resp.json()) == 0


def test_revoke_nonexistent_key(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.delete("/api/keys/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


# --- Auth required ---


def test_list_keys_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/keys")
    assert resp.status_code == 401
