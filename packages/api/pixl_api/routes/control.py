"""Session control endpoints: pause, resume, cancel, retry."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from pixl_api.deps import ProjectDB
from pixl_api.errors import EntityNotFoundError, InvalidTransitionError
from pixl_api.schemas.control import ControlResponse

router = APIRouter(prefix="/projects/{project_id}/sessions", tags=["control"])

_PAUSABLE_STATUSES = {"running", "waiting_for_gate"}
_CANCELLABLE_STATUSES = {"running", "paused", "waiting_for_gate", "pending"}


async def _get_session_or_404(db: ProjectDB, session_id: str) -> dict:
    """Fetch a session by ID or raise 404."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    if session is None:
        raise EntityNotFoundError("session", session_id)
    return session


@router.post("/{session_id}/pause", response_model=ControlResponse)
async def pause_session(db: ProjectDB, session_id: str) -> ControlResponse:
    """Pause a running session."""
    session = await _get_session_or_404(db, session_id)
    current_status = session.get("status", "")

    if current_status not in _PAUSABLE_STATUSES:
        raise InvalidTransitionError(
            "session", session_id, f"Cannot pause from status '{current_status}'"
        )

    await asyncio.to_thread(db.sessions.update_session, session_id, status="paused")
    return ControlResponse(session_id=session_id, status="paused", message="Session paused")


@router.post("/{session_id}/resume", response_model=ControlResponse)
async def resume_session(db: ProjectDB, session_id: str) -> ControlResponse:
    """Resume a paused session by setting status back to running.

    Note: This performs a state change only. Full DAG resumption from
    checkpoint requires GraphExecutor integration (deferred).
    """
    session = await _get_session_or_404(db, session_id)
    current_status = session.get("status", "")

    if current_status != "paused":
        raise InvalidTransitionError(
            "session", session_id, f"Cannot resume from status '{current_status}'"
        )

    await asyncio.to_thread(db.sessions.update_session, session_id, status="running")
    return ControlResponse(session_id=session_id, status="running", message="Session resumed")


@router.post("/{session_id}/cancel", response_model=ControlResponse)
async def cancel_session(db: ProjectDB, session_id: str) -> ControlResponse:
    """Cancel a session."""
    session = await _get_session_or_404(db, session_id)
    current_status = session.get("status", "")

    if current_status not in _CANCELLABLE_STATUSES:
        raise InvalidTransitionError(
            "session", session_id, f"Cannot cancel from status '{current_status}'"
        )

    await asyncio.to_thread(db.sessions.update_session, session_id, status="cancelled")
    return ControlResponse(session_id=session_id, status="cancelled", message="Session cancelled")


@router.post("/{session_id}/retry", response_model=ControlResponse, status_code=501)
async def retry_session(db: ProjectDB, session_id: str) -> ControlResponse:
    """Retry a failed or cancelled session.

    TODO: Wire to GraphExecutor for full DAG retry. Currently returns 501.
    """
    await _get_session_or_404(db, session_id)
    return ControlResponse(
        session_id=session_id,
        status="not_implemented",
        message="Retry requires GraphExecutor integration (not yet wired)",
    )
