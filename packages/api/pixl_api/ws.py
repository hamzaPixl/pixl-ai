"""WebSocket event stream — poll-based relay from SQLite events table.

Sends new events to connected clients every ~1s. Supports session-scoped
subscriptions via `{"subscribe": "session-id"}` messages.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pixl_api.foundation.auth.core import decode_jwt
from pixl_api.foundation.auth.secret import get_jwt_secret
from pixl_api.pool import project_pool

logger = logging.getLogger(__name__)

router = APIRouter()

POLL_INTERVAL = 1.0  # seconds


def _auth_from_token(token: str | None) -> dict[str, Any] | None:
    """Decode JWT from query param. Returns payload or None."""
    if not token:
        return None
    try:
        return decode_jwt(token, get_jwt_secret())
    except Exception:
        return None


def _fetch_new_events(
    db: Any, since: str, session_id: str | None, limit: int = 50
) -> list[dict[str, Any]]:
    """Query events newer than `since` (ISO timestamp)."""
    try:
        conn = db.conn
        if session_id:
            rows = conn.execute(
                """SELECT * FROM events
                   WHERE created_at > ? AND session_id = ?
                   ORDER BY created_at
                   LIMIT ?""",
                (since, session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM events
                   WHERE created_at > ?
                   ORDER BY created_at
                   LIMIT ?""",
                (since, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


@router.websocket("/api/ws/events/{project_id}")
async def event_stream(websocket: WebSocket, project_id: str, token: str | None = None):
    """WebSocket event stream for a project.

    Auth via ?token=JWT query parameter.
    Send {"subscribe": "session-id"} to filter by session.
    """
    # Auth
    payload = _auth_from_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await websocket.accept()

    # Get project DB
    try:
        db = project_pool.get(project_id)
    except Exception:
        await websocket.send_json({"type": "error", "message": "Project not found"})
        await websocket.close(code=4004)
        return

    session_filter: str | None = None
    last_ts = datetime.now(UTC).isoformat()

    try:
        while True:
            # Check for incoming messages (subscribe commands) — non-blocking
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=POLL_INTERVAL)
                try:
                    data = json.loads(msg)
                    if "subscribe" in data:
                        session_filter = data["subscribe"]
                        await websocket.send_json(
                            {
                                "type": "subscribed",
                                "session_id": session_filter,
                            }
                        )
                except (json.JSONDecodeError, TypeError):
                    pass
            except TimeoutError:
                pass

            # Poll for new events
            events = await asyncio.to_thread(_fetch_new_events, db, last_ts, session_filter)
            for evt in events:
                evt_ts = evt.get("created_at", "")
                if evt_ts > last_ts:
                    last_ts = evt_ts

                # Serialize payload if JSON string
                payload_raw = evt.get("payload")
                if isinstance(payload_raw, str):
                    try:
                        evt["payload"] = json.loads(payload_raw)
                    except (json.JSONDecodeError, TypeError):
                        pass

                await websocket.send_json(
                    {
                        "type": "event",
                        "event_type": evt.get("event_type", "unknown"),
                        "session_id": evt.get("session_id"),
                        "node_id": evt.get("node_id"),
                        "timestamp": evt.get("created_at"),
                        "data": evt.get("payload", {}),
                    }
                )

            # Send heartbeat ping every cycle to keep connection alive
            if not events:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected for project %s", project_id)
    except Exception as e:
        logger.warning("WebSocket error for project %s: %s", project_id, e)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
