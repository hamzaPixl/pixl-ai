"""OAuth and authentication helpers for the Gemini CLI.

The Gemini CLI authenticates via a browser-based OAuth flow that stores
credentials at ``~/.gemini/oauth_creds.json``.  Helpers here detect whether
the user has logged in and warn about the common pitfall of accidentally
using API-key billing instead of the free Ultra quota.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_OAUTH_CREDS_PATH = os.path.expanduser("~/.gemini/oauth_creds.json")


def oauth_credentials_path() -> str:
    """Return the expected path for Gemini OAuth credentials."""
    return _OAUTH_CREDS_PATH


def has_oauth_credentials() -> bool:
    """Return ``True`` if OAuth credentials exist on disk."""
    return os.path.exists(_OAUTH_CREDS_PATH)


def warn_if_api_key_set() -> None:
    """Log a warning if ``GEMINI_API_KEY`` is set in the environment.

    When the Gemini CLI detects an API key it switches from the
    quota-based Ultra billing (free ~2,000 RPD) to per-token SDK billing
    which drains the ~$100/month credit allowance rapidly.
    """
    if os.environ.get("GEMINI_API_KEY"):
        logger.warning(
            "⚠️  GEMINI_API_KEY is set — the Gemini CLI will use per-token "
            "SDK billing instead of your free Ultra quota.  Unset this "
            "variable to use OAuth-based quota billing."
        )


__all__ = [
    "oauth_credentials_path",
    "has_oauth_credentials",
    "warn_if_api_key_set",
]
