"""Route aggregation — returns all API routers."""

from __future__ import annotations

from fastapi import APIRouter

from pixl_api.routes.agents import router as agents_router
from pixl_api.routes.artifacts import router as artifacts_router
from pixl_api.routes.auth import router as auth_router
from pixl_api.routes.budget import router as budget_router
from pixl_api.routes.chains import router as chains_router
from pixl_api.routes.control import router as control_router
from pixl_api.routes.cost import router as cost_router
from pixl_api.routes.dashboard import router as dashboard_router
from pixl_api.routes.epics import router as epics_router
from pixl_api.routes.events import router as events_router
from pixl_api.routes.features import router as features_router
from pixl_api.routes.gates import router as gates_router
from pixl_api.routes.keys import router as keys_router
from pixl_api.routes.knowledge import router as knowledge_router
from pixl_api.routes.metrics import router as metrics_router
from pixl_api.routes.projects import router as projects_router
from pixl_api.routes.recovery import router as recovery_router
from pixl_api.routes.roadmaps import router as roadmaps_router
from pixl_api.routes.run import router as run_router
from pixl_api.routes.sessions import router as sessions_router
from pixl_api.routes.sessions import runs_router
from pixl_api.routes.stubs import (
    advanced_control_router,
    github_router,
    sandboxes_router,
    settings_router,
)
from pixl_api.routes.version import router as version_router
from pixl_api.routes.views import router as views_router
from pixl_api.routes.workflows import router as workflows_router
from pixl_api.routes.workspaces import router as workspaces_router


def get_api_routers() -> list[APIRouter]:
    """Return all route routers for inclusion in the app."""
    return [
        auth_router,
        projects_router,
        workflows_router,
        sessions_router,
        runs_router,
        features_router,
        epics_router,
        roadmaps_router,
        artifacts_router,
        knowledge_router,
        cost_router,
        dashboard_router,
        metrics_router,
        control_router,
        events_router,
        gates_router,
        run_router,
        agents_router,
        chains_router,
        recovery_router,
        views_router,
        budget_router,
        settings_router,
        advanced_control_router,
        workspaces_router,
        keys_router,
        github_router,
        sandboxes_router,
        version_router,
    ]
