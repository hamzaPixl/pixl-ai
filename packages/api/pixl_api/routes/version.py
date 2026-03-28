"""Version endpoint: return runtime version information."""

from __future__ import annotations

import platform
import subprocess
from functools import lru_cache

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@lru_cache(maxsize=1)
def _git_commit() -> str | None:
    """Get the current git commit hash, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


@router.get("/version")
async def get_version() -> dict[str, str | None]:
    """Return pixl version, Python version, and git commit."""
    try:
        from pixl import __version__ as engine_version
    except ImportError:
        engine_version = "unknown"

    return {
        "pixl": engine_version,
        "python": platform.python_version(),
        "git_commit": _git_commit(),
    }
