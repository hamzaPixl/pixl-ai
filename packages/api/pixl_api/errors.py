"""Domain-specific error hierarchy for the pixl API.

Re-exports the foundation error classes and adds domain-specific errors
for entity lookups, state transitions, and gate operations.
"""

from __future__ import annotations

from pixl_api.foundation.api.errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessLogicError",
    "ConflictError",
    "EntityNotFoundError",
    "GateNotWaitingError",
    "InvalidTransitionError",
    "NotFoundError",
    "ValidationError",
]


class EntityNotFoundError(NotFoundError):
    """Raised when an entity lookup returns None."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} '{entity_id}' not found")


class InvalidTransitionError(BusinessLogicError):
    """Raised when a state machine transition is rejected."""

    error_code = "INVALID_TRANSITION"

    def __init__(
        self, entity_type: str, entity_id: str, detail: str = "Transition not allowed"
    ) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(detail)


class GateNotWaitingError(BusinessLogicError):
    """Raised when a gate operation targets a gate that is not in 'waiting' state."""

    error_code = "GATE_NOT_WAITING"

    def __init__(self, gate_id: str, current_state: str) -> None:
        self.gate_id = gate_id
        self.current_state = current_state
        super().__init__(f"Gate '{gate_id}' is not waiting (state: {current_state})")
