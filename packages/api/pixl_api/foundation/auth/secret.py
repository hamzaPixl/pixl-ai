"""JWT secret key management."""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)


def _secret_file_path() -> Path:
    """Default path for the auto-generated JWT secret file."""
    return Path.home() / ".pixl" / "jwt_secret"


def get_jwt_secret() -> str:
    """Get or generate the JWT secret key.

    Reads PIXL_JWT_SECRET env var first. Falls back to reading (or generating)
    a secret file at ~/.pixl/jwt_secret with 0600 permissions.
    """
    env_secret = os.environ.get("PIXL_JWT_SECRET")
    if env_secret:
        return env_secret

    secret_path = _secret_file_path()

    if secret_path.exists():
        mode = secret_path.stat().st_mode & 0o777
        if mode != 0o600:
            logger.warning("JWT secret file has insecure permissions %04o, fixing to 0600", mode)
            secret_path.chmod(0o600)
        return secret_path.read_text().strip()

    # Generate and persist
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    new_secret = secrets.token_urlsafe(64)
    secret_path.write_text(new_secret)
    secret_path.chmod(0o600)
    return new_secret
