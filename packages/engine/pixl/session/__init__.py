"""Session management for workflow execution.

This module provides the SessionManager pattern for centralized
session state mutations with automatic observer notifications.
"""

from pixl.session.manager import SessionManager, SessionMutationError

__all__ = [
    "SessionManager",
    "SessionMutationError",
]
