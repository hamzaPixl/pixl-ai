"""Shared rate-limit header parsing utilities.

Used by providers that query their API for rate-limit metadata
(Anthropic, Codex/OpenAI).  Extracted to avoid duplicating the same
``parse_int`` / ``parse_reset`` helpers in every provider.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def parse_int(value: str | None) -> int | None:
    """Parse a string to int, returning ``None`` on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_reset_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp or seconds-from-now to a ``datetime``.

    Used by Anthropic whose ``*-reset`` headers are ISO timestamps or seconds.
    """
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            seconds = float(value)
            return datetime.now() + timedelta(seconds=seconds)
        except (ValueError, TypeError):
            return None


def parse_reset_ms(value: str | None) -> datetime | None:
    """Parse a millisecond duration (e.g. ``\"1200ms\"``) to a ``datetime``.

    Used by OpenAI/Codex whose ``x-ratelimit-reset-*`` headers are durations.
    """
    if value is None:
        return None
    try:
        ms = int(value.removesuffix("ms"))
        return datetime.now() + timedelta(milliseconds=ms)
    except (ValueError, TypeError):
        return None


__all__ = ["parse_int", "parse_reset_iso", "parse_reset_ms"]
