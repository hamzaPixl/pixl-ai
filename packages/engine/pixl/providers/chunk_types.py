"""Chunk type constants and factory functions for the provider output protocol.

All providers yield ``dict[str, Any]`` chunks.  The ``type`` field is one of
the constants here.  ``external_provider.py`` dispatches on these values.

Using constants (instead of bare strings) prevents typos and enables IDE
navigation / grep across the codebase.
"""

from __future__ import annotations

from typing import Any

# Chunk type constants

TEXT = "text"
TOOL_CALL = "tool_call"
FILE_CHANGE = "file_change"
THINKING = "thinking"
PROGRESS = "progress"
TURN_START = "turn_start"
TURN_END = "turn_end"
ERROR = "error"
START = "start"

# Factory helpers – build well-typed chunks


def text_chunk(content: str) -> dict[str, Any]:
    """Create a text chunk."""
    return {"type": TEXT, "content": content}


def tool_call_chunk(
    name: str,
    tool_input: dict[str, Any],
    *,
    output: str = "",
    exit_code: int | None = None,
) -> dict[str, Any]:
    """Create a tool-call chunk."""
    chunk: dict[str, Any] = {"type": TOOL_CALL, "tool_name": name, "tool_input": tool_input}
    if output:
        chunk["output"] = output
    if exit_code is not None:
        chunk["exit_code"] = exit_code
    return chunk


def file_change_chunk(change_type: str, file_path: str, *, diff: str = "") -> dict[str, Any]:
    """Create a file-change chunk."""
    chunk: dict[str, Any] = {
        "type": FILE_CHANGE,
        "change_type": change_type,
        "file_path": file_path,
    }
    if diff:
        chunk["diff"] = diff
    return chunk


def thinking_chunk(content: str) -> dict[str, Any]:
    """Create a thinking chunk."""
    return {"type": THINKING, "content": content}


def progress_chunk(message: str) -> dict[str, Any]:
    """Create a progress chunk."""
    return {"type": PROGRESS, "message": message}


def turn_end_chunk(usage: dict[str, Any]) -> dict[str, Any]:
    """Create a turn-end chunk with usage metadata."""
    return {"type": TURN_END, "usage": usage}


def error_chunk(content: str) -> dict[str, Any]:
    """Create an error chunk."""
    return {"type": ERROR, "content": content}


__all__ = [
    "ERROR",
    "FILE_CHANGE",
    "PROGRESS",
    "START",
    "TEXT",
    "THINKING",
    "TOOL_CALL",
    "TURN_END",
    "TURN_START",
    "error_chunk",
    "file_change_chunk",
    "progress_chunk",
    "text_chunk",
    "thinking_chunk",
    "tool_call_chunk",
    "turn_end_chunk",
]
