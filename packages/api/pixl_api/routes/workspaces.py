"""Workspace endpoints: CRUD, members, teams, invitations, projects."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from pixl_api.auth.dependencies import CurrentUser
from pixl_api.db import (
    add_team_member,
    change_member_role,
    create_invitation,
    create_team,
    create_workspace,
    delete_team,
    delete_workspace,
    get_workspace,
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
from pixl_api.errors import NotFoundError

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CreateWorkspaceRequest(BaseModel):
    name: str


class InviteRequest(BaseModel):
    email: str
    role: str = "member"


class BulkInviteRequest(BaseModel):
    invitations: list[InviteRequest]


class CreateTeamRequest(BaseModel):
    name: str
    description: str = ""
    color: str = ""


class UpdateTeamRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None


class ChangeRoleRequest(BaseModel):
    role: str


class AddTeamMemberRequest(BaseModel):
    user_id: str


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------


@router.get("")
def list_user_workspaces(user: CurrentUser) -> dict[str, Any]:
    """List workspaces the current user belongs to."""
    workspaces = list_workspaces(user["id"])
    return {"workspaces": workspaces}


@router.post("")
def create_new_workspace(user: CurrentUser, body: CreateWorkspaceRequest) -> dict[str, Any]:
    """Create a new workspace."""
    ws = create_workspace(body.name, user["id"])
    return {"workspace": ws}


@router.get("/{ws_id}")
def get_workspace_detail(ws_id: str, user: CurrentUser) -> dict[str, Any]:
    """Get workspace details."""
    ws = get_workspace(ws_id)
    if not ws:
        raise NotFoundError(f"Workspace '{ws_id}' not found")
    return {"workspace": ws}


@router.delete("/{ws_id}")
def delete_workspace_endpoint(ws_id: str, user: CurrentUser) -> dict[str, str]:
    """Delete a workspace."""
    if not delete_workspace(ws_id):
        raise NotFoundError(f"Workspace '{ws_id}' not found")
    return {"message": "Workspace deleted"}


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/{ws_id}/members")
def list_members(ws_id: str, user: CurrentUser) -> dict[str, Any]:
    """List workspace members."""
    members = list_workspace_members(ws_id)
    return {"members": members}


@router.patch("/{ws_id}/members/{user_id}/role")
def change_role(
    ws_id: str, user_id: str, body: ChangeRoleRequest, user: CurrentUser
) -> dict[str, str]:
    """Change a member's role."""
    if not change_member_role(ws_id, user_id, body.role):
        raise NotFoundError(f"Member '{user_id}' not found in workspace")
    return {"message": "Role updated"}


@router.post("/{ws_id}/leave")
def leave_workspace(ws_id: str, user: CurrentUser) -> dict[str, str]:
    """Leave a workspace."""
    remove_workspace_member(ws_id, user["id"])
    return {"message": "Left workspace"}


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post("/{ws_id}/invitations")
def invite_member(ws_id: str, body: InviteRequest, user: CurrentUser) -> dict[str, Any]:
    """Create an invitation."""
    inv = create_invitation(ws_id, body.email, body.role)
    return {"invitation": inv}


@router.post("/{ws_id}/invitations/bulk")
def bulk_invite(ws_id: str, body: BulkInviteRequest, user: CurrentUser) -> dict[str, Any]:
    """Create multiple invitations."""
    invitations = []
    for item in body.invitations:
        inv = create_invitation(ws_id, item.email, item.role)
        invitations.append(inv)
    return {"invitations": invitations}


@router.get("/{ws_id}/invitations")
def get_invitations(ws_id: str, user: CurrentUser) -> dict[str, Any]:
    """List pending invitations."""
    invitations = list_invitations(ws_id)
    return {"invitations": invitations}


@router.delete("/{ws_id}/invitations/{inv_id}")
def revoke_invitation_endpoint(ws_id: str, inv_id: str, user: CurrentUser) -> dict[str, str]:
    """Revoke an invitation."""
    if not revoke_invitation(ws_id, inv_id):
        raise NotFoundError(f"Invitation '{inv_id}' not found")
    return {"message": "Invitation revoked"}


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@router.get("/{ws_id}/teams")
def get_teams(ws_id: str, user: CurrentUser) -> dict[str, Any]:
    """List teams in a workspace."""
    teams = list_teams(ws_id)
    return {"teams": teams}


@router.post("/{ws_id}/teams")
def create_team_endpoint(ws_id: str, body: CreateTeamRequest, user: CurrentUser) -> dict[str, Any]:
    """Create a new team."""
    team = create_team(ws_id, body.name, body.description, body.color)
    return {"team": team}


@router.patch("/{ws_id}/teams/{team_id}")
def update_team_endpoint(
    ws_id: str, team_id: str, body: UpdateTeamRequest, user: CurrentUser
) -> dict[str, Any]:
    """Update a team."""
    team = update_team(
        ws_id, team_id, name=body.name, description=body.description, color=body.color
    )
    if not team:
        raise NotFoundError(f"Team '{team_id}' not found")
    return {"team": team}


@router.delete("/{ws_id}/teams/{team_id}")
def delete_team_endpoint(ws_id: str, team_id: str, user: CurrentUser) -> dict[str, str]:
    """Delete a team."""
    if not delete_team(ws_id, team_id):
        raise NotFoundError(f"Team '{team_id}' not found")
    return {"message": "Team deleted"}


# ---------------------------------------------------------------------------
# Team Members
# ---------------------------------------------------------------------------


@router.get("/{ws_id}/teams/{team_id}/members")
def get_team_members(ws_id: str, team_id: str, user: CurrentUser) -> dict[str, Any]:
    """List team members."""
    members = list_team_members(ws_id, team_id)
    return {"members": members}


@router.post("/{ws_id}/teams/{team_id}/members")
def add_team_member_endpoint(
    ws_id: str, team_id: str, body: AddTeamMemberRequest, user: CurrentUser
) -> dict[str, Any]:
    """Add a member to a team."""
    member = add_team_member(ws_id, team_id, body.user_id)
    return {"member": member}


@router.delete("/{ws_id}/teams/{team_id}/members/{user_id}")
def remove_team_member_endpoint(
    ws_id: str, team_id: str, user_id: str, user: CurrentUser
) -> dict[str, str]:
    """Remove a member from a team."""
    if not remove_team_member(ws_id, team_id, user_id):
        raise NotFoundError(f"Team member '{user_id}' not found")
    return {"message": "Team member removed"}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.get("/{ws_id}/projects")
def get_projects(ws_id: str, user: CurrentUser) -> dict[str, Any]:
    """List projects linked to a workspace."""
    projects = list_workspace_projects(ws_id)
    return {"projects": projects}


@router.post("/{ws_id}/projects/{project_id}/link")
def link_project_endpoint(ws_id: str, project_id: str, user: CurrentUser) -> dict[str, Any]:
    """Link a project to a workspace."""
    project = link_project(ws_id, project_id)
    return {"project": project}
