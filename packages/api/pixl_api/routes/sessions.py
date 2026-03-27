"""Session endpoints: list, get, get node instance."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.helpers import get_or_404
from pixl_api.schemas.sessions import NodeInstanceResponse, SessionDetail, SessionListEntry

router = APIRouter(prefix="/projects/{project_id}/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionListEntry])
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


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    db: ProjectDB,
    session_id: str,
) -> dict[str, Any]:
    """Get session details including node instances."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    return get_or_404(session, "session", session_id)


@router.get("/{session_id}/nodes/{node_id}", response_model=NodeInstanceResponse)
async def get_node_instance(
    db: ProjectDB,
    session_id: str,
    node_id: str,
) -> dict[str, Any]:
    """Get a specific node instance within a session."""
    # Verify session exists
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    get_or_404(session, "session", session_id)

    node = await asyncio.to_thread(db.sessions.get_node_instance, session_id, node_id)
    return get_or_404(node, "node_instance", node_id)
