"""API key endpoints: list, create, revoke."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from pixl_api.auth.dependencies import CurrentUser
from pixl_api.db import create_api_key, list_api_keys, revoke_api_key
from pixl_api.errors import NotFoundError

router = APIRouter(prefix="/keys", tags=["keys"])


class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: list[str] = []
    rate_limit_rpm: int = 60


@router.get("")
def list_keys(user: CurrentUser) -> list[dict[str, Any]]:
    """List active API keys for the current user."""
    return list_api_keys(user["id"])


@router.post("")
def create_key(user: CurrentUser, body: CreateApiKeyRequest) -> dict[str, Any]:
    """Create a new API key. The raw key is returned only once."""
    return create_api_key(user["id"], body.name, body.scopes, body.rate_limit_rpm)


@router.delete("/{key_id}")
def revoke_key(key_id: str, user: CurrentUser) -> dict[str, str]:
    """Revoke an API key."""
    if not revoke_api_key(key_id, user["id"]):
        raise NotFoundError(f"API key '{key_id}' not found")
    return {"message": "API key revoked"}
