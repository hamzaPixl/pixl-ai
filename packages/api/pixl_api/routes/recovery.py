"""Recovery endpoints: blocked node inbox, retry, and skip."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB
from pixl_api.schemas.recovery import BlockedNodeResponse, RecoveryActionResponse

router = APIRouter(prefix="/projects/{project_id}/recovery", tags=["recovery"])


def _get_projection_store(db: ProjectDB):  # noqa: ANN202
    """Instantiate ProjectionStore from the project database."""
    from pixl.storage.db.projections import ProjectionStore

    return ProjectionStore(db)


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
    result = await asyncio.to_thread(_do_retry_node, db, session_id, node_id)
    return result


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
    result = await asyncio.to_thread(_do_skip_node, db, session_id, node_id)
    return result


def _do_retry_node(db: Any, session_id: str, node_id: str) -> dict[str, Any]:
    """Sync helper: reset a blocked node to pending."""
    conn = db.conn
    row = conn.execute(
        "SELECT state FROM node_instances WHERE session_id = ? AND node_id = ?",
        (session_id, node_id),
    ).fetchone()
    if row is None:
        from pixl_api.errors import EntityNotFoundError

        raise EntityNotFoundError("node_instance", f"{session_id}/{node_id}")

    current_state = row["state"]
    if current_state != "task_blocked":
        from pixl_api.errors import InvalidTransitionError

        raise InvalidTransitionError(
            "node_instance",
            node_id,
            f"Node is '{current_state}', not 'task_blocked'",
        )

    conn.execute(
        """UPDATE node_instances
           SET state = 'task_pending',
               blocked_reason = NULL,
               error_message = NULL,
               failure_kind = NULL,
               started_at = NULL,
               ended_at = NULL
           WHERE session_id = ? AND node_id = ?""",
        (session_id, node_id),
    )
    conn.commit()

    return {
        "session_id": session_id,
        "node_id": node_id,
        "action": "retry",
        "status": "task_pending",
        "message": "Node reset to pending for retry",
    }


def _do_skip_node(db: Any, session_id: str, node_id: str) -> dict[str, Any]:
    """Sync helper: mark a blocked node as skipped."""
    conn = db.conn
    row = conn.execute(
        "SELECT state FROM node_instances WHERE session_id = ? AND node_id = ?",
        (session_id, node_id),
    ).fetchone()
    if row is None:
        from pixl_api.errors import EntityNotFoundError

        raise EntityNotFoundError("node_instance", f"{session_id}/{node_id}")

    current_state = row["state"]
    if current_state != "task_blocked":
        from pixl_api.errors import InvalidTransitionError

        raise InvalidTransitionError(
            "node_instance",
            node_id,
            f"Node is '{current_state}', not 'task_blocked'",
        )

    from datetime import datetime

    conn.execute(
        """UPDATE node_instances
           SET state = 'task_skipped',
               blocked_reason = NULL,
               ended_at = ?
           WHERE session_id = ? AND node_id = ?""",
        (datetime.now().isoformat(), session_id, node_id),
    )
    conn.commit()

    return {
        "session_id": session_id,
        "node_id": node_id,
        "action": "skip",
        "status": "task_skipped",
        "message": "Node skipped",
    }
