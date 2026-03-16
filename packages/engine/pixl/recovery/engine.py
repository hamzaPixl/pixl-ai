"""Recovery engine — thin wrapper that emits auditable events around policy decisions."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from pixl.errors import PixlError

if TYPE_CHECKING:
    from pixl.recovery.incident_store import IncidentStore
from pixl.models.event import Event, EventType
from pixl.recovery.policy import RecoveryDecision, decide_recovery

logger = logging.getLogger(__name__)


class RecoveryEngine:
    """Evaluates recovery policy and emits structured events.

    Args:
        session_id: Workflow session ID for event attribution.
        emit_event: Callback to persist/broadcast an Event.
    """

    def __init__(
        self,
        session_id: str,
        emit_event: Callable[[Event], None],
        incident_store: IncidentStore | None = None,
    ) -> None:
        self.session_id = session_id
        self._emit_event = emit_event
        self._incident_store = incident_store

    def evaluate(
        self,
        error: PixlError,
        node_id: str,
        attempt: int,
        max_attempts: int | None = None,
    ) -> RecoveryDecision:
        """Run recovery policy and emit request + decision events.

        Args:
            error: The typed error that triggered recovery.
            node_id: The node that failed.
            attempt: Current attempt number (0-based).
            max_attempts: Optional global max-attempts override.

        Returns:
            The RecoveryDecision from the policy engine.
        """
        # 1. Emit RECOVERY_REQUESTED
        logger.info(
            "recovery.requested",
            extra={"node_id": node_id, "error_type": error.error_type, "attempt": attempt},
        )
        self._emit_event(
            Event.create(
                EventType.RECOVERY_REQUESTED,
                self.session_id,
                node_id=node_id,
                data={
                    "error_type": error.error_type,
                    "message": error.message,
                    "is_transient": error.is_transient,
                    "attempt": attempt,
                    "metadata": error.metadata,
                },
            )
        )

        # 2. Evaluate policy (pure function)
        decision = decide_recovery(
            error,
            attempt,
            incident_store=self._incident_store,
            max_attempts_override=max_attempts,
        )

        # 3. Emit RECOVERY_DECISION
        logger.info(
            "recovery.decision",
            extra={
                "node_id": node_id,
                "action": decision.action.value,
                "should_execute": decision.should_execute,
            },
        )
        self._emit_event(
            Event.create(
                EventType.RECOVERY_DECISION,
                self.session_id,
                node_id=node_id,
                data={
                    "action": decision.action.value,
                    "reason": decision.reason,
                    "max_attempts": decision.max_attempts,
                    "current_attempt": decision.current_attempt,
                    "backoff_seconds": decision.backoff_seconds,
                    "should_execute": decision.should_execute,
                },
            )
        )

        return decision
