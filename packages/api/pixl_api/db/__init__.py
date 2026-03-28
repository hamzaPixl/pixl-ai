"""Database package — re-exports all public functions for backward compatibility.

Existing imports like ``from pixl_api.db import create_user`` continue to work.
"""

from __future__ import annotations

from pixl_api.db._connection import DB_PATH, get_connection, init_db
from pixl_api.db.api_keys import create_api_key, list_api_keys, revoke_api_key
from pixl_api.db.invitations import create_invitation, list_invitations, revoke_invitation
from pixl_api.db.projects import link_project, list_workspace_projects
from pixl_api.db.teams import (
    add_team_member,
    create_team,
    delete_team,
    list_team_members,
    list_teams,
    remove_team_member,
    update_team,
)
from pixl_api.db.users import (
    complete_onboarding,
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    update_password,
    update_user,
)
from pixl_api.db.workspaces import (
    _ensure_member,
    add_workspace_member,
    change_member_role,
    create_workspace,
    delete_workspace,
    ensure_workspace,
    get_default_workspace,
    get_workspace,
    list_workspace_members,
    list_workspaces,
    remove_workspace_member,
)

__all__ = [
    # Connection / init
    "DB_PATH",
    "get_connection",
    "init_db",
    # Users
    "complete_onboarding",
    "create_user",
    "delete_user",
    "get_user_by_email",
    "get_user_by_id",
    "update_password",
    "update_user",
    # Workspaces
    "_ensure_member",
    "add_workspace_member",
    "change_member_role",
    "create_workspace",
    "delete_workspace",
    "ensure_workspace",
    "get_default_workspace",
    "get_workspace",
    "list_workspace_members",
    "list_workspaces",
    "remove_workspace_member",
    # Teams
    "add_team_member",
    "create_team",
    "delete_team",
    "list_team_members",
    "list_teams",
    "remove_team_member",
    "update_team",
    # Invitations
    "create_invitation",
    "list_invitations",
    "revoke_invitation",
    # Projects
    "link_project",
    "list_workspace_projects",
    # API Keys
    "create_api_key",
    "list_api_keys",
    "revoke_api_key",
]
