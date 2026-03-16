"""Typed Pydantic models for the Gemini CLI ``stream-json`` event protocol.

The Gemini CLI emits newline-delimited JSON (JSONL) events when invoked with
``--output-format stream-json``.  Each line is one of the event types modelled
here.

The :func:`parse_event` factory takes a raw ``dict`` and returns the
appropriate typed model, falling back to :class:`UnknownEvent` for
unrecognised event types.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Base

class _EventBase(BaseModel):
    """Common base for all stream-json events."""

    type: str

# Concrete event types

class InitEvent(_EventBase):
    """Session initialization metadata (emitted once at stream start)."""

    type: Literal["init"] = "init"
    session_id: str = ""
    model: str = ""

class MessageEvent(_EventBase):
    """An assistant or system message chunk."""

    type: Literal["message"] = "message"
    role: str = "assistant"
    content: str | None = None

class ToolUseEvent(_EventBase):
    """The model has invoked a tool."""

    type: Literal["tool_use"] = "tool_use"
    tool_name: str = "Tool"
    tool_id: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)

class ToolResultEvent(_EventBase):
    """Result of a previously invoked tool."""

    type: Literal["tool_result"] = "tool_result"
    tool_id: str = ""
    status: str = ""
    output: str | None = None
    error: dict[str, Any] | str | None = None

class ErrorEvent(_EventBase):
    """Error or warning emitted by the CLI."""

    type: Literal["error"] = "error"
    message: str = ""
    severity: str = "error"

class ResultEvent(_EventBase):
    """End-of-turn result with optional usage stats."""

    type: Literal["result"] = "result"
    text: str = ""
    status: str = ""
    stats: dict[str, Any] | None = None
    error: dict[str, Any] | str | None = None

class UnknownEvent(_EventBase):
    """Catch-all for unrecognised event types; preserves the raw payload."""

    raw: dict[str, Any] = Field(default_factory=dict)

# Discriminated union

GeminiEvent = (
    InitEvent
    | MessageEvent
    | ToolUseEvent
    | ToolResultEvent
    | ErrorEvent
    | ResultEvent
    | UnknownEvent
)

_EVENT_MAP: dict[str, type[_EventBase]] = {
    "init": InitEvent,
    "message": MessageEvent,
    "tool_use": ToolUseEvent,
    "tool_result": ToolResultEvent,
    "error": ErrorEvent,
    "result": ResultEvent,
}

def parse_event(raw: dict[str, Any]) -> GeminiEvent:
    """Construct the appropriate typed event from a raw JSON dict.

    Unknown event types are wrapped in :class:`UnknownEvent`.
    """
    event_type = str(raw.get("type", ""))
    cls = _EVENT_MAP.get(event_type)
    if cls is None:
        return UnknownEvent(type=event_type, raw=raw)
    return cls.model_validate(raw)

__all__ = [
    "GeminiEvent",
    "InitEvent",
    "MessageEvent",
    "ToolUseEvent",
    "ToolResultEvent",
    "ErrorEvent",
    "ResultEvent",
    "UnknownEvent",
    "parse_event",
]
