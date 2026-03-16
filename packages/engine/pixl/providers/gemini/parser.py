"""JSONL parser for the Gemini CLI ``stream-json`` output.

Responsibilities:
- Parse individual lines of newline-delimited JSON into typed
  :class:`~pixl.providers.gemini.models.GeminiEvent` instances.
- Extract usage / token stats from both ``stream-json`` result events
  and the legacy ``json`` response payload.
- Robust fallback for malformed lines.
"""

from __future__ import annotations

import json
from typing import Any

from pixl.providers.gemini.models import GeminiEvent, parse_event

# Line-level parsing

def parse_line(line: str) -> GeminiEvent | None:
    """Parse a single JSONL line into a typed event.

    Returns ``None`` for blank or malformed lines.
    """
    stripped = line.strip()
    if not stripped:
        return None

    try:
        raw = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if not isinstance(raw, dict):
        return None

    return parse_event(raw)

# JSON payload helpers (used by the ``--output-format json`` fallback)

def parse_json_payload(text: str) -> dict[str, Any] | None:
    """Best-effort parse of a full JSON payload from CLI stdout.

    Handles both clean JSON and text that has a JSON object embedded inside.
    """
    if not text:
        return None

    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
        return None
    except json.JSONDecodeError:
        # Try extracting an embedded JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            payload = json.loads(text[start : end + 1])
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
    return None

# Usage / stats extraction

def extract_usage_from_stream_stats(stats: Any) -> dict[str, Any] | None:
    """Extract token counts from a ``result`` event's ``stats`` field."""
    if not isinstance(stats, dict):
        return None

    usage: dict[str, Any] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = stats.get(key)
        if isinstance(value, int):
            usage[key] = value

    return usage or None

def extract_usage_from_json_stats(stats: Any) -> dict[str, Any] | None:
    """Extract token counts from the ``json`` fallback ``stats`` field.

    Handles both the direct format and the nested ``models.*.tokens`` format.
    """
    if not isinstance(stats, dict):
        return None

    # Try direct format first
    direct = extract_usage_from_stream_stats(stats)
    if direct:
        return direct

    # Session metrics format: {"models": {"<model>": {"tokens": {...}}}}
    models = stats.get("models")
    if not isinstance(models, dict):
        return None

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    found = False

    for model_data in models.values():
        if not isinstance(model_data, dict):
            continue
        tokens = model_data.get("tokens")
        if not isinstance(tokens, dict):
            continue

        prompt = tokens.get("prompt")
        candidates = tokens.get("candidates")
        total = tokens.get("total")

        if isinstance(prompt, int):
            input_tokens += prompt
            found = True
        if isinstance(candidates, int):
            output_tokens += candidates
            found = True
        if isinstance(total, int):
            total_tokens += total
            found = True

    if not found:
        return None

    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }

__all__ = [
    "parse_line",
    "parse_json_payload",
    "extract_usage_from_stream_stats",
    "extract_usage_from_json_stats",
]
