"""Tests for workspace route endpoints."""

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
    monkeypatch.setattr("pixl_api.db._connection.DB_PATH", db_path)
    init_db()


@pytest.fixture()
def user_and_token() -> dict[str, Any]:
    """Create a test user with workspace and return user dict + JWT token."""
    user = create_user("test@example.com", "hashed_pw", "Test", "User")
    ws = ensure_workspace(user["id"])
    token = encode_jwt({"sub": user["id"], "email": user["email"]}, get_jwt_secret())
    return {"user": user, "workspace": ws, "token": token}


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def auth_headers(user_and_token: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_and_token['token']}"}


# --- GET /workspaces ---


def test_list_workspaces(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    resp = client.get("/api/workspaces", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "workspaces" in data
    assert len(data["workspaces"]) >= 1
    assert data["workspaces"][0]["id"] == user_and_token["workspace"]["id"]


# --- POST /workspaces ---


def test_create_workspace(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/workspaces",
        headers=auth_headers,
        json={"name": "New WS"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "workspace" in data
    assert data["workspace"]["name"] == "New WS"


# --- GET /workspaces/{id} ---


def test_get_workspace(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    resp = client.get(f"/api/workspaces/{ws_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "workspace" in data
    assert data["workspace"]["id"] == ws_id


def test_get_workspace_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    # Nonexistent workspace returns 403 (user is not a member)
    resp = client.get("/api/workspaces/nonexistent", headers=auth_headers)
    assert resp.status_code == 403


# --- Authorization ---


def test_non_member_cannot_access_workspace(
    client: TestClient, user_and_token: dict[str, Any]
) -> None:
    """A user who is not a member of a workspace should get 403."""
    ws_id = user_and_token["workspace"]["id"]
    # Create a second user who is NOT a member of the workspace
    other_user = create_user("other@example.com", "hashed_pw", "Other", "User")
    other_token = encode_jwt(
        {"sub": other_user["id"], "email": other_user["email"]}, get_jwt_secret()
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}

    resp = client.get(f"/api/workspaces/{ws_id}", headers=other_headers)
    assert resp.status_code == 403

    resp = client.get(f"/api/workspaces/{ws_id}/members", headers=other_headers)
    assert resp.status_code == 403

    resp = client.get(f"/api/workspaces/{ws_id}/teams", headers=other_headers)
    assert resp.status_code == 403

    resp = client.get(f"/api/workspaces/{ws_id}/projects", headers=other_headers)
    assert resp.status_code == 403

    resp = client.get(f"/api/workspaces/{ws_id}/invitations", headers=other_headers)
    assert resp.status_code == 403


def test_member_can_access_workspace(client: TestClient, user_and_token: dict[str, Any]) -> None:
    """A user who has been added as a member should get 200."""
    ws_id = user_and_token["workspace"]["id"]
    member = create_user("member@example.com", "hashed_pw", "Member", "User")
    from pixl_api.db import add_workspace_member

    add_workspace_member(ws_id, member["id"], "member")
    member_token = encode_jwt({"sub": member["id"], "email": member["email"]}, get_jwt_secret())
    member_headers = {"Authorization": f"Bearer {member_token}"}

    resp = client.get(f"/api/workspaces/{ws_id}", headers=member_headers)
    assert resp.status_code == 200


# --- GET /workspaces/{id}/members ---


def test_list_members(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    resp = client.get(f"/api/workspaces/{ws_id}/members", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "members" in data
    assert len(data["members"]) >= 1


# --- POST /workspaces/{id}/invitations ---


def test_create_invitation(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    resp = client.post(
        f"/api/workspaces/{ws_id}/invitations",
        headers=auth_headers,
        json={"email": "invited@example.com", "role": "member"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "invitation" in data
    assert data["invitation"]["email"] == "invited@example.com"


# --- GET /workspaces/{id}/invitations ---


def test_list_invitations(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    # Create one first
    client.post(
        f"/api/workspaces/{ws_id}/invitations",
        headers=auth_headers,
        json={"email": "inv@example.com", "role": "member"},
    )
    resp = client.get(f"/api/workspaces/{ws_id}/invitations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "invitations" in data
    assert len(data["invitations"]) >= 1


# --- DELETE /workspaces/{id}/invitations/{inv_id} ---


def test_revoke_invitation(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    create_resp = client.post(
        f"/api/workspaces/{ws_id}/invitations",
        headers=auth_headers,
        json={"email": "torevoke@example.com", "role": "member"},
    )
    inv_id = create_resp.json()["invitation"]["id"]
    resp = client.delete(f"/api/workspaces/{ws_id}/invitations/{inv_id}", headers=auth_headers)
    assert resp.status_code == 200


# --- Teams ---


def test_create_and_list_teams(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    resp = client.post(
        f"/api/workspaces/{ws_id}/teams",
        headers=auth_headers,
        json={"name": "Engineering", "description": "Dev team", "color": "#00ff00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "team" in data
    assert data["team"]["name"] == "Engineering"

    resp = client.get(f"/api/workspaces/{ws_id}/teams", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["teams"]) >= 1


# --- PATCH /workspaces/{id}/teams/{team_id} ---


def test_update_team(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    create_resp = client.post(
        f"/api/workspaces/{ws_id}/teams",
        headers=auth_headers,
        json={"name": "Old Name"},
    )
    team_id = create_resp.json()["team"]["id"]
    resp = client.patch(
        f"/api/workspaces/{ws_id}/teams/{team_id}",
        headers=auth_headers,
        json={"name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["team"]["name"] == "New Name"


# --- DELETE /workspaces/{id}/teams/{team_id} ---


def test_delete_team(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    create_resp = client.post(
        f"/api/workspaces/{ws_id}/teams",
        headers=auth_headers,
        json={"name": "To Delete"},
    )
    team_id = create_resp.json()["team"]["id"]
    resp = client.delete(f"/api/workspaces/{ws_id}/teams/{team_id}", headers=auth_headers)
    assert resp.status_code == 200


# --- Projects ---


def test_link_and_list_projects(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    resp = client.post(
        f"/api/workspaces/{ws_id}/projects/proj-1/link",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    resp = client.get(f"/api/workspaces/{ws_id}/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["projects"]) >= 1


# --- PATCH /workspaces/{id}/members/{user_id}/role ---


def test_change_member_role(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    ws_id = user_and_token["workspace"]["id"]
    # Add a second user
    user2 = create_user("user2@example.com", "hash2", "User", "Two")
    from pixl_api.db import add_workspace_member

    add_workspace_member(ws_id, user2["id"], "member")
    resp = client.patch(
        f"/api/workspaces/{ws_id}/members/{user2['id']}/role",
        headers=auth_headers,
        json={"role": "admin"},
    )
    assert resp.status_code == 200


# --- POST /workspaces/{id}/leave ---


def test_leave_workspace(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    # Create a second workspace to leave
    resp = client.post(
        "/api/workspaces",
        headers=auth_headers,
        json={"name": "Leave WS"},
    )
    ws_id = resp.json()["workspace"]["id"]
    resp = client.post(f"/api/workspaces/{ws_id}/leave", headers=auth_headers)
    assert resp.status_code == 200


# --- DELETE /workspaces/{id} ---


def test_delete_workspace(
    client: TestClient, auth_headers: dict[str, str], user_and_token: dict[str, Any]
) -> None:
    # Create a workspace to delete (not the default one)
    resp = client.post(
        "/api/workspaces",
        headers=auth_headers,
        json={"name": "Delete WS"},
    )
    ws_id = resp.json()["workspace"]["id"]
    resp = client.delete(f"/api/workspaces/{ws_id}", headers=auth_headers)
    assert resp.status_code == 200


# --- Auth required ---


def test_list_workspaces_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/workspaces")
    assert resp.status_code == 401
