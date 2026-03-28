"""Auth business logic: signup, login, token refresh, current user."""

from __future__ import annotations

from typing import Any

from pixl_api.db import (
    complete_onboarding as db_complete_onboarding,
)
from pixl_api.db import (
    create_user,
    delete_user,
    ensure_workspace,
    get_user_by_email,
    get_user_by_id,
    update_password,
    update_user,
)
from pixl_api.errors import AuthenticationError, ConflictError, ValidationError
from pixl_api.foundation.auth.core import (
    decode_jwt,
    encode_jwt,
    hash_password,
    verify_password,
)
from pixl_api.foundation.auth.secret import get_jwt_secret


def _safe_user(user: dict[str, Any]) -> dict[str, Any]:
    """Strip password_hash from a user dict."""
    return {k: v for k, v in user.items() if k != "password_hash"}


def _build_token(user: dict[str, Any]) -> str:
    """Create a JWT for the given user."""
    return encode_jwt({"sub": user["id"], "email": user["email"]}, get_jwt_secret())


def signup(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> dict[str, Any]:
    """Create a user, default workspace, and return auth payload."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")

    existing = get_user_by_email(email.lower())
    if existing:
        raise ConflictError("Email already registered")

    pw_hash = hash_password(password)
    user = create_user(email.lower(), pw_hash, first_name, last_name)
    workspace = ensure_workspace(user["id"])
    token = _build_token(user)

    return {"user": _safe_user(user), "token": token, "workspace_id": workspace["id"]}


def login(email: str, password: str) -> dict[str, Any]:
    """Verify credentials and return auth payload."""
    user = get_user_by_email(email.lower())
    if not user:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user["password_hash"]):
        raise AuthenticationError("Invalid email or password")

    workspace = ensure_workspace(user["id"])
    token = _build_token(user)

    return {"user": _safe_user(user), "token": token, "workspace_id": workspace["id"]}


def refresh_token(token: str) -> dict[str, Any]:
    """Decode an existing token and issue a fresh one."""
    try:
        payload = decode_jwt(token, get_jwt_secret())
    except Exception:
        raise AuthenticationError("Token cannot be refreshed") from None

    user = get_user_by_id(payload["sub"])
    if not user:
        raise AuthenticationError("User not found")

    new_token = _build_token(user)
    return {"token": new_token}


def get_current_user_data(token: str) -> dict[str, Any]:
    """Decode JWT and return the user record (without password_hash)."""
    try:
        payload = decode_jwt(token, get_jwt_secret())
    except Exception:
        raise AuthenticationError("Invalid or expired token") from None

    user = get_user_by_id(payload["sub"])
    if not user:
        raise AuthenticationError("User not found")

    workspace = ensure_workspace(user["id"])
    return {"user": _safe_user(user), "workspace_id": workspace["id"]}


def mark_onboarding_complete(user_id: str) -> None:
    """Mark onboarding as complete for a user."""
    db_complete_onboarding(user_id)


def update_profile(user_id: str, **fields: str) -> dict[str, Any]:
    """Update user profile fields."""
    allowed = {"first_name", "last_name", "theme", "avatar"}
    filtered = {k: v for k, v in fields.items() if k in allowed and v is not None}
    updated = update_user(user_id, **filtered)
    if not updated:
        raise AuthenticationError("User not found")
    return {"user": updated}


def change_password(user_id: str, current_password: str, new_password: str) -> dict[str, str]:
    """Change user password after verifying the current one."""
    user = get_user_by_id(user_id)
    if not user:
        raise AuthenticationError("User not found")

    if not verify_password(current_password, user["password_hash"]):
        raise AuthenticationError("Current password is incorrect")

    if len(new_password) < 8:
        raise ValidationError("New password must be at least 8 characters")

    new_hash = hash_password(new_password)
    update_password(user_id, new_hash)
    return {"message": "Password changed successfully"}


def delete_account(user_id: str, password: str) -> dict[str, str]:
    """Delete user account after verifying password."""
    user = get_user_by_id(user_id)
    if not user:
        raise AuthenticationError("User not found")

    if not verify_password(password, user["password_hash"]):
        raise AuthenticationError("Password is incorrect")

    delete_user(user_id)
    return {"message": "Account deleted"}
