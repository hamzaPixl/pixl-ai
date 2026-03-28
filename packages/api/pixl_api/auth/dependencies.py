"""FastAPI dependency injection for authentication."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request

from pixl_api.auth.service import get_current_user_data
from pixl_api.errors import AuthenticationError
from pixl_api.foundation.auth.core import get_token_from_request


def get_current_user(request: Request) -> dict[str, Any]:
    """Extract JWT from request and return the authenticated user dict.

    Raises AuthenticationError when the token is missing or invalid.
    """
    token = get_token_from_request(request)
    if not token:
        raise AuthenticationError("Not authenticated")

    data = get_current_user_data(token)
    return data["user"]


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
