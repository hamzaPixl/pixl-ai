"""Gate endpoints: list gates, approve, reject."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB
from pixl_api.errors import EntityNotFoundError, GateNotWaitingError
from pixl_api.helpers import get_or_404, safe_emit
from pixl_api.schemas.gates import GateActionRequest, GateResponse

router = APIRouter(prefix="/projects/{project_id}/gates", tags=["gates"])


def _extract_gates(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract gate node instances from a session dict."""
    nodes = session.get("node_instances", {})
    gates: list[dict[str, Any]] = []
    for node_id, node in nodes.items():
        node_type = node.get("node_type", node.get("type", ""))
        if node_type == "gate":
            gates.append(
                {
                    "id": node.get("id", node_id),
                    "session_id": session["id"],
                    "node_id": node_id,
                    "status": node.get("status", "unknown"),
                    "requested_at": node.get("started_at"),
                }
            )
    return gates


@router.get("/{session_id}", response_model=list[GateResponse])
async def list_gates(
    db: ProjectDB,
    session_id: str,
) -> list[dict[str, Any]]:
    """List gate nodes for a session."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    session = get_or_404(session, "session", session_id)
    return _extract_gates(session)


@router.post("/{session_id}/{gate_id}/approve", response_model=GateResponse)
async def approve_gate(
    db: ProjectDB,
    session_id: str,
    gate_id: str,
    body: GateActionRequest | None = None,
) -> dict[str, Any]:
    """Approve a waiting gate."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    session = get_or_404(session, "session", session_id)

    node = await asyncio.to_thread(db.sessions.get_node_instance, session_id, gate_id)
    if node is None:
        raise EntityNotFoundError("gate", gate_id)

    status = node.get("status", "")
    if status != "waiting_for_gate":
        raise GateNotWaitingError(gate_id, status)

    await asyncio.to_thread(
        db.sessions.upsert_node_instance,
        session_id,
        gate_id,
        state="task_completed",
    )
    safe_emit(db, session_id=session_id, node_id=gate_id, event_type="gate.approved")

    return {
        "id": gate_id,
        "session_id": session_id,
        "node_id": gate_id,
        "status": "task_completed",
        "requested_at": node.get("started_at"),
    }


@router.post("/{session_id}/{gate_id}/reject", response_model=GateResponse)
async def reject_gate(
    db: ProjectDB,
    session_id: str,
    gate_id: str,
    body: GateActionRequest | None = None,
) -> dict[str, Any]:
    """Reject a waiting gate."""
    session = await asyncio.to_thread(db.sessions.get_session, session_id)
    session = get_or_404(session, "session", session_id)

    node = await asyncio.to_thread(db.sessions.get_node_instance, session_id, gate_id)
    if node is None:
        raise EntityNotFoundError("gate", gate_id)

    status = node.get("status", "")
    if status != "waiting_for_gate":
        raise GateNotWaitingError(gate_id, status)

    note = body.note if body else None
    await asyncio.to_thread(
        db.sessions.upsert_node_instance,
        session_id,
        gate_id,
        state="task_failed",
        blocked_reason=note or "Gate rejected",
    )
    safe_emit(db, session_id=session_id, node_id=gate_id, event_type="gate.rejected")

    return {
        "id": gate_id,
        "session_id": session_id,
        "node_id": gate_id,
        "status": "task_failed",
        "requested_at": node.get("started_at"),
    }
