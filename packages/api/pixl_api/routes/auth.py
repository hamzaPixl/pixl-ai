"""Auth endpoints: signup, login, logout, me, refresh."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from pixl_api.auth import service as auth_service
from pixl_api.auth.dependencies import CurrentUser
from pixl_api.errors import AuthenticationError
from pixl_api.foundation.auth.core import (
    clear_auth_cookie,
    get_token_from_request,
    set_auth_cookie,
)
from pixl_api.schemas.auth import AuthResponse, LoginRequest, SignupRequest, TokenResponse


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    theme: str | None = None
    avatar: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    password: str


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest, response: Response) -> dict[str, Any]:
    """Create a new user account."""
    result = auth_service.signup(body.email, body.password, body.first_name, body.last_name)
    set_auth_cookie(response, result["token"])
    return result


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, response: Response) -> dict[str, Any]:
    """Authenticate and get a JWT token."""
    result = auth_service.login(body.email, body.password)
    set_auth_cookie(response, result["token"])
    return result


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    """Clear the auth cookie."""
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me")
def get_me(user: CurrentUser, request: Request) -> dict[str, Any]:
    """Get current authenticated user."""
    data = auth_service.get_current_user_data(get_token_from_request(request))  # type: ignore[arg-type]
    return data


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response) -> dict[str, Any]:
    """Refresh the JWT token."""
    token = get_token_from_request(request)
    if not token:
        raise AuthenticationError("No token provided")

    result = auth_service.refresh_token(token)
    set_auth_cookie(response, result["token"])
    return result


@router.patch("/me")
def update_profile(user: CurrentUser, body: UpdateProfileRequest) -> dict[str, Any]:
    """Update current user profile."""
    return auth_service.update_profile(
        user["id"],
        **body.model_dump(exclude_none=True),
    )


@router.post("/me/onboarding-complete")
def complete_onboarding(user: CurrentUser) -> dict[str, str]:
    """Mark onboarding as complete."""
    auth_service.mark_onboarding_complete(user["id"])
    return {"message": "Onboarding complete"}


@router.post("/me/password")
def change_password(user: CurrentUser, body: ChangePasswordRequest) -> dict[str, str]:
    """Change current user's password."""
    return auth_service.change_password(user["id"], body.current_password, body.new_password)


@router.post("/me/delete")
def delete_account(
    user: CurrentUser, body: DeleteAccountRequest, response: Response
) -> dict[str, str]:
    """Delete current user's account."""
    result = auth_service.delete_account(user["id"], body.password)
    clear_auth_cookie(response)
    return result
