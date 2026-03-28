"""Recovery endpoints: blocked node inbox, retry, and skip."""

from __future__ import annotations

import asyncio
from typing import Any, Never

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectDB
from pixl_api.schemas.recovery import BlockedNodeResponse, RecoveryActionResponse

router = APIRouter(prefix="/projects/{project_id}/recovery", tags=["recovery"])


def _get_projection_store(db: ProjectDB):  # noqa: ANN202
    """Instantiate ProjectionStore from the project database."""
    from pixl.storage.db.projections import ProjectionStore

    return ProjectionStore(db)


@router.get("/{session_id}/explain")
async def recovery_explain(db: ProjectDB, session_id: str) -> dict[str, Any]:
    """Get recovery context for a session: blocked nodes, failure info."""
    store = _get_projection_store(db)
    inbox = await asyncio.to_thread(store.recovery_inbox)
    session_items = [item for item in inbox if item.get("session_id") == session_id]
    return {
        "session_id": session_id,
        "blocked_nodes": session_items,
        "count": len(session_items),
    }


@router.get("/incidents")
async def list_incidents(
    db: ProjectDB,
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset"),
) -> list[dict[str, Any]]:
    """List recovery incidents."""
    records = await asyncio.to_thread(db.incidents.list_recent, limit=limit, offset=offset)
    return [r.to_dict() if hasattr(r, "to_dict") else r for r in records]


@router.get("/inbox", response_model=list[BlockedNodeResponse])
async def recovery_inbox(db: ProjectDB) -> list[dict[str, Any]]:
    """List blocked nodes awaiting human intervention."""
    store = _get_projection_store(db)
    return await asyncio.to_thread(store.recovery_inbox)


@router.post(
    "/{session_id}/{node_id}/retry",
    response_model=RecoveryActionResponse,
)
async def retry_blocked_node(
    db: ProjectDB,
    session_id: str,
    node_id: str,
) -> dict[str, Any]:
    """Retry a blocked node by unblocking it back to pending.

    Resets the node state from task_blocked to task_pending so the
    executor picks it up on the next cycle.
    """
    try:
        return await asyncio.to_thread(
            db.sessions.retry_blocked_node,  # type: ignore[attr-defined]
            session_id,
            node_id,
        )
    except ValueError as exc:
        _raise_api_error(str(exc), session_id, node_id)


@router.post(
    "/{session_id}/{node_id}/skip",
    response_model=RecoveryActionResponse,
)
async def skip_blocked_node(
    db: ProjectDB,
    session_id: str,
    node_id: str,
) -> dict[str, Any]:
    """Skip a blocked node by marking it as skipped/completed."""
    try:
        return await asyncio.to_thread(
            db.sessions.skip_blocked_node,  # type: ignore[attr-defined]
            session_id,
            node_id,
        )
    except ValueError as exc:
        _raise_api_error(str(exc), session_id, node_id)


def _raise_api_error(message: str, session_id: str, node_id: str) -> Never:
    """Convert ValueError from engine into the appropriate API error."""
    from pixl_api.errors import EntityNotFoundError, InvalidTransitionError

    if "not found" in message:
        raise EntityNotFoundError("node_instance", f"{session_id}/{node_id}")
    raise InvalidTransitionError("node_instance", node_id, message)
