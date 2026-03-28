"""Tests for workspace-related database functions."""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl_api.db import (
    add_team_member,
    add_workspace_member,
    change_member_role,
    create_invitation,
    create_team,
    create_user,
    create_workspace,
    delete_team,
    delete_workspace,
    ensure_workspace,
    get_workspace,
    init_db,
    link_project,
    list_invitations,
    list_team_members,
    list_teams,
    list_workspace_members,
    list_workspace_projects,
    list_workspaces,
    remove_team_member,
    remove_workspace_member,
    revoke_invitation,
    update_team,
)


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect DB_PATH to a temp directory for every test."""
    db_path = tmp_path / "api.db"
    monkeypatch.setattr("pixl_api.db.DB_PATH", db_path)
    init_db()


# --- Workspace CRUD ---


def test_create_workspace_returns_workspace() -> None:
    user = create_user("owner@example.com", "hash")
    ws = create_workspace("My Workspace", user["id"])
    assert ws["name"] == "My Workspace"
    assert ws["owner_id"] == user["id"]
    assert "id" in ws
    assert "created_at" in ws


def test_create_workspace_auto_adds_owner_as_admin_member() -> None:
    user = create_user("owner2@example.com", "hash")
    ws = create_workspace("Test WS", user["id"])
    members = list_workspace_members(ws["id"])
    assert len(members) == 1
    assert members[0]["user_id"] == user["id"]
    assert members[0]["role"] == "admin"


def test_get_workspace() -> None:
    user = create_user("get@example.com", "hash")
    ws = create_workspace("Get WS", user["id"])
    fetched = get_workspace(ws["id"])
    assert fetched is not None
    assert fetched["id"] == ws["id"]
    assert fetched["name"] == "Get WS"


def test_get_workspace_not_found() -> None:
    assert get_workspace("nonexistent") is None


def test_list_workspaces_for_user() -> None:
    user = create_user("lister@example.com", "hash")
    create_workspace("WS A", user["id"])
    create_workspace("WS B", user["id"])
    workspaces = list_workspaces(user["id"])
    assert len(workspaces) == 2
    names = {w["name"] for w in workspaces}
    assert names == {"WS A", "WS B"}


def test_list_workspaces_includes_member_workspaces() -> None:
    owner = create_user("owner3@example.com", "hash")
    member = create_user("member3@example.com", "hash")
    ws = create_workspace("Shared WS", owner["id"])
    add_workspace_member(ws["id"], member["id"], "member")
    workspaces = list_workspaces(member["id"])
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "Shared WS"


def test_delete_workspace() -> None:
    user = create_user("deleter@example.com", "hash")
    ws = create_workspace("To Delete", user["id"])
    assert delete_workspace(ws["id"])
    assert get_workspace(ws["id"]) is None


def test_delete_workspace_nonexistent() -> None:
    assert not delete_workspace("nonexistent")


# --- ensure_workspace now auto-adds member ---


def test_ensure_workspace_adds_owner_as_admin_member() -> None:
    user = create_user("ensure@example.com", "hash")
    ws = ensure_workspace(user["id"])
    members = list_workspace_members(ws["id"])
    assert len(members) == 1
    assert members[0]["user_id"] == user["id"]
    assert members[0]["role"] == "admin"


# --- Members ---


def test_add_and_list_workspace_members() -> None:
    owner = create_user("mowner@example.com", "hash")
    member = create_user("mmember@example.com", "hash")
    ws = create_workspace("Members WS", owner["id"])
    add_workspace_member(ws["id"], member["id"], "member")
    members = list_workspace_members(ws["id"])
    assert len(members) == 2  # owner + member
    roles = {m["user_id"]: m["role"] for m in members}
    assert roles[owner["id"]] == "admin"
    assert roles[member["id"]] == "member"


def test_change_member_role() -> None:
    owner = create_user("chowner@example.com", "hash")
    member = create_user("chmember@example.com", "hash")
    ws = create_workspace("Role WS", owner["id"])
    add_workspace_member(ws["id"], member["id"], "member")
    assert change_member_role(ws["id"], member["id"], "admin")
    members = list_workspace_members(ws["id"])
    roles = {m["user_id"]: m["role"] for m in members}
    assert roles[member["id"]] == "admin"


def test_remove_workspace_member() -> None:
    owner = create_user("rmowner@example.com", "hash")
    member = create_user("rmmember@example.com", "hash")
    ws = create_workspace("Remove WS", owner["id"])
    add_workspace_member(ws["id"], member["id"], "member")
    assert remove_workspace_member(ws["id"], member["id"])
    members = list_workspace_members(ws["id"])
    assert len(members) == 1
    assert members[0]["user_id"] == owner["id"]


# --- Invitations ---


def test_create_and_list_invitations() -> None:
    owner = create_user("inv_owner@example.com", "hash")
    ws = create_workspace("Inv WS", owner["id"])
    inv = create_invitation(ws["id"], "invite@example.com", "member")
    assert inv["email"] == "invite@example.com"
    assert inv["role"] == "member"
    assert inv["status"] == "pending"
    invitations = list_invitations(ws["id"])
    assert len(invitations) == 1
    assert invitations[0]["id"] == inv["id"]


def test_revoke_invitation() -> None:
    owner = create_user("rev_owner@example.com", "hash")
    ws = create_workspace("Rev WS", owner["id"])
    inv = create_invitation(ws["id"], "revoke@example.com", "member")
    assert revoke_invitation(ws["id"], inv["id"])
    invitations = list_invitations(ws["id"])
    assert len(invitations) == 0


def test_revoke_invitation_nonexistent() -> None:
    owner = create_user("rev2_owner@example.com", "hash")
    ws = create_workspace("Rev2 WS", owner["id"])
    assert not revoke_invitation(ws["id"], "nonexistent")


# --- Teams ---


def test_create_and_list_teams() -> None:
    owner = create_user("team_owner@example.com", "hash")
    ws = create_workspace("Team WS", owner["id"])
    team = create_team(ws["id"], "Engineering", "Dev team", "#ff0000")
    assert team["name"] == "Engineering"
    assert team["description"] == "Dev team"
    assert team["color"] == "#ff0000"
    teams = list_teams(ws["id"])
    assert len(teams) == 1
    assert teams[0]["id"] == team["id"]


def test_update_team() -> None:
    owner = create_user("upteam_owner@example.com", "hash")
    ws = create_workspace("UpTeam WS", owner["id"])
    team = create_team(ws["id"], "Old Name", "", "")
    updated = update_team(ws["id"], team["id"], name="New Name")
    assert updated is not None
    assert updated["name"] == "New Name"


def test_update_team_nonexistent() -> None:
    owner = create_user("upteam2_owner@example.com", "hash")
    ws = create_workspace("UpTeam2 WS", owner["id"])
    assert update_team(ws["id"], "nonexistent") is None


def test_delete_team() -> None:
    owner = create_user("delteam_owner@example.com", "hash")
    ws = create_workspace("DelTeam WS", owner["id"])
    team = create_team(ws["id"], "To Delete", "", "")
    assert delete_team(ws["id"], team["id"])
    assert len(list_teams(ws["id"])) == 0


def test_delete_team_nonexistent() -> None:
    owner = create_user("delteam2_owner@example.com", "hash")
    ws = create_workspace("DelTeam2 WS", owner["id"])
    assert not delete_team(ws["id"], "nonexistent")


# --- Team members ---


def test_add_and_list_team_members() -> None:
    owner = create_user("tmowner@example.com", "hash")
    member = create_user("tmmember@example.com", "hash")
    ws = create_workspace("TM WS", owner["id"])
    team = create_team(ws["id"], "Team A", "", "")
    add_team_member(ws["id"], team["id"], owner["id"])
    add_team_member(ws["id"], team["id"], member["id"])
    members = list_team_members(ws["id"], team["id"])
    assert len(members) == 2
    user_ids = {m["user_id"] for m in members}
    assert owner["id"] in user_ids
    assert member["id"] in user_ids


def test_remove_team_member() -> None:
    owner = create_user("rtmowner@example.com", "hash")
    member = create_user("rtmmember@example.com", "hash")
    ws = create_workspace("RTM WS", owner["id"])
    team = create_team(ws["id"], "Team B", "", "")
    add_team_member(ws["id"], team["id"], owner["id"])
    add_team_member(ws["id"], team["id"], member["id"])
    assert remove_team_member(ws["id"], team["id"], member["id"])
    members = list_team_members(ws["id"], team["id"])
    assert len(members) == 1


# --- Workspace projects ---


def test_link_and_list_workspace_projects() -> None:
    owner = create_user("proj_owner@example.com", "hash")
    ws = create_workspace("Proj WS", owner["id"])
    link_project(ws["id"], "project-123")
    link_project(ws["id"], "project-456")
    projects = list_workspace_projects(ws["id"])
    assert len(projects) == 2
    pids = {p["project_id"] for p in projects}
    assert pids == {"project-123", "project-456"}


def test_link_project_idempotent() -> None:
    owner = create_user("proj2_owner@example.com", "hash")
    ws = create_workspace("Proj2 WS", owner["id"])
    link_project(ws["id"], "project-789")
    link_project(ws["id"], "project-789")  # Should not raise
    projects = list_workspace_projects(ws["id"])
    assert len(projects) == 1
