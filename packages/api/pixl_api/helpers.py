"""Shared utility functions for API route handlers."""

from __future__ import annotations

import logging
from typing import Any

from pixl.storage.db.connection import PixlDB

from pixl_api.errors import EntityNotFoundError

logger = logging.getLogger(__name__)


def get_or_404[T](value: T | None, entity_type: str, entity_id: str) -> T:
    """Return *value* if not None, otherwise raise EntityNotFoundError."""
    if value is None:
        raise EntityNotFoundError(entity_type, entity_id)
    return value


def safe_emit(
    db: PixlDB,
    *,
    session_id: str,
    node_id: str,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Emit an event, logging failures instead of raising.

    Wraps db.events.emit so callers never need try/except for
    best-effort event recording.
    """
    try:
        db.events.emit(
            event_type=event_type,
            entity_type="node",
            entity_id=node_id,
            payload={"session_id": session_id, **(data or {})},
        )
    except Exception:
        logger.exception(
            "Failed to emit %s event for node %s in session %s",
            event_type,
            node_id,
            session_id,
        )
