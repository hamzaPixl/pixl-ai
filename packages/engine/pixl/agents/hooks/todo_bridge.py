"""Bridge SDK TodoWrite tool updates to engine event store.

Captures TodoWrite PostToolUse calls and emits structured events
into the engine's EventDB, enabling progress tracking and analytics
for agent task lists.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def create_todo_tracking_callback(
    emit_event: Callable[..., Any],
    session_id: str | None = None,
    node_id: str | None = None,
) -> Callable[[str, dict[str, Any]], None]:
    """Create a callback that logs TodoWrite tool calls as engine events.

    The returned callback matches the ``on_tool_call`` / ``on_post_tool_call``
    signature used by ``build_sdk_options``: ``(tool_name, tool_input) -> None``.

    Args:
        emit_event: ``EventDB.emit`` or any callable accepting keyword args
            ``event_type``, ``session_id``, ``node_id``, and ``payload``.
        session_id: Current workflow session ID (forwarded to every event).
        node_id: Current node ID (forwarded to every event).
    """

    def callback(tool_name: str, tool_input: dict[str, Any]) -> None:
        if tool_name != "TodoWrite":
            return

        todos = tool_input.get("todos", [])
        for todo in todos:
            status = todo.get("status", "unknown")
            content = todo.get("content", "")
            try:
                emit_event(
                    event_type="todo_update",
                    session_id=session_id,
                    node_id=node_id,
                    payload={
                        "content": content,
                        "status": status,
                        "active_form": todo.get("activeForm"),
                    },
                )
            except Exception:
                logger.debug("Failed to emit todo_update event", exc_info=True)

    return callback
