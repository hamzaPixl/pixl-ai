"""Core authentication: JWT encode/decode, bcrypt passwords, cookie helpers."""

from __future__ import annotations

import os
import time
from typing import Any

import bcrypt
import jwt
from fastapi import Request, Response

ALGORITHM = "HS256"
COOKIE_NAME = "auth"
ACCESS_TOKEN_MAX_AGE = 24 * 60 * 60  # 24 hours
_GRACE_PERIOD_SECONDS = 60


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def encode_jwt(payload: dict[str, Any], secret: str, expiry_hours: int = 24) -> str:
    """Encode a JWT with expiry. Adds iat and exp claims automatically."""
    now = int(time.time())
    data = {**payload, "iat": now, "exp": now + expiry_hours * 3600}
    return jwt.encode(data, secret, algorithm=ALGORITHM)


def decode_jwt(token: str, secret: str) -> dict[str, Any]:
    """Decode a JWT token with a 60-second grace period for expired tokens.

    Raises jwt.InvalidTokenError on invalid tokens.
    Raises jwt.ExpiredSignatureError if expired beyond the grace period.
    """
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        unverified: dict[str, Any] = jwt.decode(
            token, secret, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
        exp = unverified.get("exp", 0)
        if time.time() - exp < _GRACE_PERIOD_SECONDS:
            return unverified
        raise


def get_token_from_request(request: Request) -> str | None:
    """Extract JWT from Authorization header (Bearer) or 'auth' cookie.

    Header takes precedence over cookie.
    """
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return request.cookies.get(COOKIE_NAME)


def set_auth_cookie(
    response: Response,
    token: str,
    max_age: int = ACCESS_TOKEN_MAX_AGE,
) -> None:
    """Set the auth cookie on a response (env-aware secure flag)."""
    is_production = os.environ.get("PIXL_ENV", "development") == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear the auth cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
