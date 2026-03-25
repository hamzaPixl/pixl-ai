"""Event emission extracted from GraphExecutor.

Handles all event persistence, broadcasting, and transition commits.
GraphExecutor delegates to this class for all event-related operations.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pixl.errors import PixlError, StorageError
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState

if TYPE_CHECKING:
    from pixl.models.session import WorkflowSession

logger = logging.getLogger(__name__)


class EventEmitter:
    """Manages event persistence, broadcasting, and transition commits.

    Extracted from GraphExecutor to isolate event emission concerns.
    """

    def __init__(
        self,
        *,
        session_id: str,
        store: Any,  # WorkflowSessionStore — avoid circular import
        event_callback: Callable[[Event], None] | None = None,
        incident_store_getter: Callable[[], Any] | None = None,
    ) -> None:
        """Initialize the event emitter.

        Args:
            session_id: ID of the current session (for error events).
            store: WorkflowSessionStore for persistence.
            event_callback: Optional callback for real-time event streaming.
            incident_store_getter: Lazy getter for the incident store
                (used for recording recovery incidents).
        """
        self.session_id = session_id
        self.store = store
        self.event_callback = event_callback
        self._incident_store_getter = incident_store_getter

    def emit_event(self, event: Event) -> None:
        """Emit event to store and callback.

        Args:
            event: Event to emit
        """
        try:
            self.store.append_event(event)
        except StorageError as exc:
            # Best-effort error event for storage failures
            self.emit_error_event(exc, node_id=event.node_id)
            raise

        if self.event_callback:
            self.event_callback(event)

    def emit_events_batch(self, events: list[Event]) -> None:
        """Emit multiple events in a single DB transaction.

        Falls back to per-event emission on batch failure.
        """
        if not events:
            return
        try:
            self.store.append_events_batch(events)
        except Exception:
            logger.warning(
                "Batch event emission failed, falling back to individual emission",
                exc_info=True,
            )
            # Fallback to individual emission
            for event in events:
                self.emit_event(event)
            return

        if self.event_callback:
            for event in events:
                self.event_callback(event)

    def emit_error_event(self, error: PixlError, node_id: str | None = None) -> Event | None:
        """Emit a structured error event."""
        event = Event.error(
            self.session_id,
            message=error.message,
            error_type=error.error_type,
            node_id=node_id,
            metadata=error.metadata,
            is_transient=error.is_transient,
            cause=str(error.cause) if error.cause else None,
        )
        try:
            self.store.append_event(event)
        except StorageError as db_exc:
            # DB is authoritative; if it fails, log and propagate
            logger.error(
                "Failed to persist error event for node %s: %s",
                node_id,
                db_exc,
            )

        if self.event_callback:
            self.event_callback(event)
        return event

    def persist_event(self, event: Event) -> None:
        """Persist a pre-built Event to storage and broadcast via callback.

        Used as RecoveryEngine's emit_event callback so recovery events
        are always auditable. Logs warnings on persistence failure.

        Also writes incident records for terminal recovery events.
        """
        persisted = False
        try:
            self.store.append_event(event)
            persisted = True
        except StorageError as db_exc:
            logger.warning(
                "Failed to persist recovery event %s to DB: %s",
                event.type.value,
                db_exc,
            )

        if not persisted:
            logger.error(
                "Recovery event %s for node %s lost — DB persistence failed",
                event.type.value,
                event.node_id,
            )

        if event.type in (
            EventType.RECOVERY_SUCCEEDED,
            EventType.RECOVERY_FAILED,
            EventType.RECOVERY_ESCALATED,
        ):
            if self._incident_store_getter:
                try:
                    self._incident_store_getter().record_from_event(event)
                except Exception as exc:
                    # Don't fail recovery if incident recording fails
                    logger.debug(
                        "Failed to record incident for event %s: %s",
                        event.type.value,
                        exc,
                    )

        if self.event_callback:
            self.event_callback(event)

    def commit_transition(
        self,
        *,
        session: WorkflowSession,
        event_type: EventType,
        node_id: str | None,
        payload: dict[str, Any] | None,
        from_state: NodeState | None,
        to_state: NodeState | None,
    ) -> Event:
        """Commit an event + session state update atomically."""
        event = self.store.commit_transition(
            session,
            node_id=node_id,
            from_state=from_state.value if from_state else None,
            to_state=to_state.value if to_state else None,
            event_type=event_type,
            payload=payload or {},
        )
        if self.event_callback:
            self.event_callback(event)
        return event

    def checkpoint(
        self,
        *,
        session: WorkflowSession,
        reason: str | None = None,
    ) -> Event:
        """Persist a checkpoint event and session snapshot."""
        return self.commit_transition(
            session=session,
            event_type=EventType.CHECKPOINT_SAVED,
            node_id=None,
            payload={"reason": reason} if reason else {},
            from_state=None,
            to_state=None,
        )
