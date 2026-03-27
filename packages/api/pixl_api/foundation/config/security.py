"""Security configuration: CORS and JWT secret validation."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MIN_SECRET_LENGTH = 32


def get_cors_config(origins: list[str]) -> dict[str, Any]:
    """Build CORS middleware kwargs for FastAPI's CORSMiddleware.

    Args:
        origins: List of allowed origin URLs.

    Returns:
        Dict suitable for unpacking into CORSMiddleware constructor.
    """
    return {
        "allow_origins": origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }


def validate_jwt_secret(secret: str) -> None:
    """Warn if the JWT secret is too short for production use.

    Logs a warning if the secret is shorter than 32 characters.
    """
    if len(secret) < _MIN_SECRET_LENGTH:
        logger.warning(
            "JWT secret is too short (%d chars). Use at least %d characters for production.",
            len(secret),
            _MIN_SECRET_LENGTH,
        )
