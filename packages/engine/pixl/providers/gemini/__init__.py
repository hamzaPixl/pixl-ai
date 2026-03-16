"""Gemini CLI SDK — typed async Python wrapper for the Gemini CLI.

Public API
----------
.. autosummary::

    GeminiCLIClient
    GeminiEvent
    MessageEvent
    ToolUseEvent
    ToolResultEvent
    ErrorEvent
    ResultEvent
    parse_event
"""

from pixl.providers.gemini.client import (
    CLINotFoundError,
    GeminiCLIClient,
    OAuthNotConfiguredError,
)
from pixl.providers.gemini.models import (
    ErrorEvent,
    GeminiEvent,
    MessageEvent,
    ResultEvent,
    ToolResultEvent,
    ToolUseEvent,
    UnknownEvent,
    parse_event,
)

__all__ = [
    "CLINotFoundError",
    "ErrorEvent",
    "GeminiCLIClient",
    "GeminiEvent",
    "MessageEvent",
    "OAuthNotConfiguredError",
    "ResultEvent",
    "ToolResultEvent",
    "ToolUseEvent",
    "UnknownEvent",
    "parse_event",
]
