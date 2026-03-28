"""Session endpoints: list, get, get node instance, heartbeat runs."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.helpers import get_or_404

router = APIRouter(prefix="/projects/{project_id}/sessions", tags=["sessions"])


@router.get("/active")
async def active_sessions(db: ProjectDB) -> list[dict[str, Any]]:
    """List sessions that haven't ended yet."""
    return await asyncio.to_thread(db.sessions.get_active_sessions)


@router.get("")
async def list_sessions(
    db: ProjectDB,
    feature_id: str | None = Query(None, description="Filter by feature ID"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[dict[str, Any]]:
    """List workflow sessions for a project."""
    return await asyncio.to_thread(
        db.sessions.list_sessions,
        feature_id=feature_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}")
async def get_session(
    db: ProjectDB,
    session_id: str,
) -> dict[str, Any]:
    """Get session details including node instances."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    return get_or_404(session, "session", session_id)


@router.get(
    "/{session_id}/nodes",
)
async def list_node_instances(
    db: ProjectDB,
    session_id: str,
) -> list[dict[str, Any]]:
    """List all node instances for a session."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    get_or_404(session, "session", session_id)
    node_map = session.get("node_instances", {})  # type: ignore[union-attr]
    return list(node_map.values())


@router.get(
    "/{session_id}/nodes/{node_id}",
)
async def get_node_instance(
    db: ProjectDB,
    session_id: str,
    node_id: str,
) -> dict[str, Any]:
    """Get a specific node instance within a session."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    get_or_404(session, "session", session_id)

    node = await asyncio.to_thread(db.sessions.get_node_instance, session_id, node_id)
    return get_or_404(node, "node_instance", node_id)


@router.post("/{session_id}/report-draft")
async def draft_report(
    db: ProjectDB,
    session_id: str,
) -> dict[str, Any]:
    """Enqueue a session report draft job."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    get_or_404(session, "session", session_id)
    return await asyncio.to_thread(
        db.sessions.enqueue_or_get_inflight_session_report_job,
        session_id=session_id,
    )


@router.get("/{session_id}/report-jobs")
async def list_report_jobs(
    db: ProjectDB,
    session_id: str,
    limit: int = Query(10, ge=1, le=50, description="Max results"),
) -> list[dict[str, Any]]:
    """List report jobs for a session."""
    return await asyncio.to_thread(
        db.sessions.list_session_report_jobs,
        session_id=session_id,
        limit=limit,
    )


@router.get("/{session_id}/artifacts")
async def list_session_artifacts(
    db: ProjectDB,
    session_id: str,
) -> list[dict[str, Any]]:
    """List artifacts for a specific session."""
    return await asyncio.to_thread(
        db.artifacts.list_page, session_id=session_id, limit=200, offset=0
    )


@router.get("/{session_id}/runs")
async def list_heartbeat_runs(
    db: ProjectDB,
    session_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max results"),
) -> list[dict[str, Any]]:
    """List heartbeat runs for a session."""
    return await asyncio.to_thread(db.heartbeat_runs.list_for_session, session_id, limit=limit)


@router.get("/{session_id}/runs/active")
async def get_active_run(
    db: ProjectDB,
    session_id: str,
) -> dict[str, Any]:
    """Get the currently active heartbeat run for a session."""
    run = await asyncio.to_thread(db.heartbeat_runs.get_active_run, session_id)
    return {"active_run": run}


# Stalled runs — mounted under /projects/{project_id}/runs
runs_router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])


@runs_router.get("/stalled")
async def stalled_runs(
    db: ProjectDB,
    threshold: int = Query(60, ge=10, le=600, description="Stalled threshold in seconds"),
) -> list[dict[str, Any]]:
    """Find heartbeat runs that appear stalled (no heartbeat within threshold)."""
    return await asyncio.to_thread(db.heartbeat_runs.find_stalled_runs, threshold)
