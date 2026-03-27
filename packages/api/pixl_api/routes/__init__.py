"""Route aggregation — returns all API routers."""

from __future__ import annotations

from fastapi import APIRouter

from pixl_api.routes.auth import router as auth_router
from pixl_api.routes.control import router as control_router
from pixl_api.routes.events import router as events_router
from pixl_api.routes.gates import router as gates_router
from pixl_api.routes.projects import router as projects_router
from pixl_api.routes.run import router as run_router
from pixl_api.routes.sessions import router as sessions_router
from pixl_api.routes.workflows import router as workflows_router


def get_api_routers() -> list[APIRouter]:
    """Return all route routers for inclusion in the app."""
    return [
        auth_router,
        projects_router,
        workflows_router,
        sessions_router,
        control_router,
        events_router,
        gates_router,
        run_router,
    ]
