"""Stub endpoints for platform features not yet implemented.

Returns 501 Not Implemented with descriptive messages to prevent Console crashes.
These are SaaS-layer features deferred post-MVP.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

# GitHub integration
github_router = APIRouter(prefix="/github", tags=["github"])


@github_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
@github_router.api_route("", methods=["GET", "POST"])
async def github_stub(request: Request) -> JSONResponse:
    """GitHub integration endpoints — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "GitHub integration not yet implemented (post-MVP)"},
    )


# Sandboxes
sandboxes_router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])


@sandboxes_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
@sandboxes_router.api_route("", methods=["GET", "POST"])
async def sandboxes_stub(request: Request) -> JSONResponse:
    """Sandbox endpoints — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Sandboxes not yet implemented (post-MVP)"},
    )


# Project Settings (env vars, github link, general)
settings_router = APIRouter(prefix="/projects/{project_id}/settings", tags=["settings"])


@settings_router.get("/general")
async def get_general_settings(project_id: str) -> dict[str, Any]:
    """Get general project settings."""
    from pixl.projects.registry import get_project

    project = get_project(project_id)
    if not project:
        return {
            "project_id": project_id,
            "name": project_id,
            "description": "",
            "project_root": None,
        }
    return {
        "project_id": project_id,
        "name": project.get("name", project_id),
        "description": project.get("description", ""),
        "project_root": str(project.get("root", "")),
    }


@settings_router.patch("/general")
async def update_general_settings(project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Update general project settings — stub."""
    return {
        "project_id": project_id,
        "name": body.get("name", project_id),
        "description": body.get("description", ""),
        "project_root": None,
    }


@settings_router.api_route("/env-vars/{path:path}", methods=["GET", "POST", "DELETE"])
@settings_router.api_route("/env-vars", methods=["GET", "POST"])
async def env_vars_stub(request: Request, project_id: str) -> JSONResponse:
    """Env vars endpoints — not yet implemented."""
    if request.method == "GET":
        return JSONResponse(status_code=200, content=[])
    return JSONResponse(
        status_code=501,
        content={"detail": "Env vars not yet implemented (post-MVP)"},
    )


@settings_router.api_route("/github/{path:path}", methods=["GET", "POST", "DELETE"])
@settings_router.api_route("/github", methods=["GET"])
async def settings_github_stub(request: Request, project_id: str) -> JSONResponse:
    """GitHub settings endpoints — not yet implemented."""
    if request.method == "GET":
        return JSONResponse(status_code=200, content=None)
    return JSONResponse(
        status_code=501,
        content={"detail": "GitHub settings not yet implemented (post-MVP)"},
    )


# Advanced control stubs (autonomy, rerun, rollback, epic control)
advanced_control_router = APIRouter(prefix="/projects/{project_id}", tags=["advanced-control"])


@advanced_control_router.put("/features/{feature_id}/autonomy")
async def set_autonomy_stub(
    project_id: str, feature_id: str, body: dict[str, Any]
) -> dict[str, Any]:
    """Set feature autonomy mode — stub."""
    return {
        "feature_id": feature_id,
        "mode": body.get("mode", "assist"),
        "message": "Autonomy mode set (stub)",
    }


@advanced_control_router.post("/sessions/{session_id}/rerun-from/{node_id}")
async def rerun_from_stub(project_id: str, session_id: str, node_id: str) -> JSONResponse:
    """Rerun from node — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Rerun-from requires GraphExecutor integration (post-MVP)"},
    )


@advanced_control_router.post("/sessions/{session_id}/nodes/{node_id}/rerun")
async def rerun_node_stub(project_id: str, session_id: str, node_id: str) -> JSONResponse:
    """Rerun single node — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Node rerun requires GraphExecutor integration (post-MVP)"},
    )


@advanced_control_router.post("/sessions/{session_id}/rollback")
async def rollback_stub(project_id: str, session_id: str) -> JSONResponse:
    """Rollback session — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Rollback requires GraphExecutor integration (post-MVP)"},
    )


@advanced_control_router.get("/epics/{epic_id}/waves")
async def epic_waves_stub(project_id: str, epic_id: str) -> JSONResponse:
    """Epic waves — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Epic waves not yet implemented (post-MVP)"},
    )


@advanced_control_router.get("/epics/{epic_id}/execution")
async def epic_execution_stub(project_id: str, epic_id: str) -> JSONResponse:
    """Epic execution progress — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Epic execution not yet implemented (post-MVP)"},
    )


@advanced_control_router.post("/epics/{epic_id}/run")
async def run_epic_stub(project_id: str, epic_id: str) -> JSONResponse:
    """Run epic — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Epic run not yet implemented (post-MVP)"},
    )


@advanced_control_router.post("/epics/{epic_id}/cancel")
async def cancel_epic_stub(project_id: str, epic_id: str) -> JSONResponse:
    """Cancel epic execution — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Epic cancel not yet implemented (post-MVP)"},
    )


# Chain control stubs
@advanced_control_router.get("/chains/{chain_id}/signals")
async def chain_signals_stub(project_id: str, chain_id: str) -> JSONResponse:
    """Chain signals — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Chain signals not yet implemented (post-MVP)"},
    )


@advanced_control_router.get("/chains/{chain_id}/quality")
async def chain_quality_stub(project_id: str, chain_id: str) -> JSONResponse:
    """Chain quality — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Chain quality not yet implemented (post-MVP)"},
    )


@advanced_control_router.post("/chains/{chain_id}/pause")
@advanced_control_router.post("/chains/{chain_id}/resume")
@advanced_control_router.post("/chains/{chain_id}/cancel")
@advanced_control_router.post("/chains/{chain_id}/reset")
async def chain_control_stub(project_id: str, chain_id: str) -> JSONResponse:
    """Chain control operations — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Chain control not yet implemented (post-MVP)"},
    )


# Quality trends
@advanced_control_router.get("/quality/trends")
async def quality_trends_stub(project_id: str) -> JSONResponse:
    """Quality trends — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Quality trends not yet implemented (post-MVP)"},
    )
