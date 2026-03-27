"""Route aggregation — returns all API routers."""

from __future__ import annotations

from fastapi import APIRouter

from pixl_api.routes.auth import router as auth_router


def get_api_routers() -> list[APIRouter]:
    """Return all route routers for inclusion in the app."""
    return [
        auth_router,
    ]
