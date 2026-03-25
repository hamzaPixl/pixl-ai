"""Envelope extraction for structured stage output (FALLBACK path).

.. deprecated:: 10.0.0
    Primary structured output is now enforced by the SDK via ``output_format``
    (JSON schema constrained decoding). This module is kept as a fallback for
    external providers (Gemini, OpenAI) and crash recovery.

Extracts `<pixl_output>{...}</pixl_output>` envelopes from agent
result text and parses them into StageOutput models.
"""

from __future__ import annotations

import json
import logging
import re

from pixl.models.stage_output import StageOutput

logger = logging.getLogger(__name__)

# Regex to match the envelope. Use last occurrence if multiple.
_ENVELOPE_RE = re.compile(
    r"<pixl_output>\s*(.*?)\s*</pixl_output>",
    re.DOTALL,
)


def _extract_tag(body: str, tag: str) -> str | None:
    """Extract text from a simple XML-like tag."""
    pattern = re.compile(rf"<{tag}>\s*(.*?)\s*</{tag}>", re.DOTALL | re.IGNORECASE)
    match = pattern.search(body)
    return match.group(1).strip() if match else None


def _parse_optional_json(value: str | None, default: object) -> object:
    """Parse JSON when present, returning a default on parse failure."""
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _coerce_xml_like_envelope(body: str) -> dict | None:
    """Coerce XML-like envelope content into a StageOutput-compatible dict.

    Some models return:
        <pixl_output>
          <schema_version>1.0</schema_version>
          ...
        </pixl_output>
    instead of JSON between the envelope tags. This parser performs a
    best-effort coercion to keep execution moving.
    """
    if "<" not in body or ">" not in body:
        return None

    stage_id = _extract_tag(body, "stage_id")
    if not stage_id:
        return None

    schema_version = _extract_tag(body, "schema_version") or "1.0"
    raw_status = (_extract_tag(body, "status") or "ok").strip().lower()
    status_map = {
        "completed": "ok",
        "complete": "ok",
        "success": "ok",
        "succeeded": "ok",
        "ok": "ok",
        "error": "error",
        "failed": "error",
        "failure": "error",
    }
    status = status_map.get(raw_status, "ok")

    raw_summary = _extract_tag(body, "summary")
    if raw_summary:
        try:
            parsed_summary = json.loads(raw_summary)
            if isinstance(parsed_summary, list):
                summary = [str(item) for item in parsed_summary if str(item).strip()]
            elif isinstance(parsed_summary, str):
                # wrapping the whole string as a single item (avoids char-by-char
                # downstream processing when summary is a plain paragraph).
                parts = [line.strip() for line in parsed_summary.split("\n") if line.strip()]
                summary = parts[:10] if parts else []
            else:
                summary = [str(parsed_summary)]
        except json.JSONDecodeError:
            # Not valid JSON — treat the raw XML text as a plain summary
            parts = [line.strip() for line in raw_summary.split("\n") if line.strip()]
            summary = parts[:10] if parts else [raw_summary]
    else:
        summary = []

    artifacts_written = _parse_optional_json(_extract_tag(body, "artifacts_written"), default=[])
    if not isinstance(artifacts_written, list):
        artifacts_written = []

    included_sources = _parse_optional_json(_extract_tag(body, "included_sources"), default=[])
    if not isinstance(included_sources, list):
        included_sources = []

    payload = _parse_optional_json(_extract_tag(body, "payload"), default={})
    if not isinstance(payload, dict):
        payload = {"value": payload}

    next_data = _parse_optional_json(_extract_tag(body, "next"), default=None)
    if next_data is not None and not isinstance(next_data, dict):
        next_data = None

    error_data = _parse_optional_json(_extract_tag(body, "error"), default=None)
    if error_data is not None and not isinstance(error_data, dict):
        error_data = None

    coerced: dict = {
        "schema_version": schema_version,
        "stage_id": stage_id,
        "status": status,
        "summary": summary,
        "artifacts_written": artifacts_written,
        "included_sources": included_sources,
        "payload": payload,
    }
    if next_data is not None:
        coerced["next"] = next_data
    if error_data is not None:
        coerced["error"] = error_data
    return coerced


def _sanitize_json(json_str: str) -> str:
    """Strip comments and trailing commas from LLM-produced JSON."""
    text = re.sub(r"//[^\n]*", "", json_str)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _try_parse_json(json_str: str) -> dict | None:
    """Parse JSON with escalating repair strategies.

    1. ``json.loads`` (fast path)
    2. Regex sanitization (comments, trailing commas)
    3. ``json-repair`` (handles more exotic malformations)

    Returns a parsed dict or None.
    """
    # 1. Fast path
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Regex sanitization
    try:
        data = json.loads(_sanitize_json(json_str))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    # 3. json-repair (heavy)
    try:
        from json_repair import repair_json

        repaired = str(repair_json(json_str, return_objects=False))
        data = json.loads(repaired)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return None


def _validate_stage_output(data: dict) -> StageOutput | None:
    """Validate a dict as a StageOutput, returning None on failure."""
    try:
        return StageOutput.model_validate(data)
    except Exception:
        return None


def _extract_fallback_json(text: str) -> dict | None:
    """Scan agent output for a JSON object that looks like a StageOutput.

    When no `<pixl_output>` tags are found, this function scans the last
    8000 characters for `{...}` blocks and returns the first dict that
    contains a ``stage_id`` key.

    Args:
        text: Full agent result text.

    Returns:
        Parsed dict with ``stage_id`` key, or None.
    """
    tail = text[-8000:] if len(text) > 8000 else text

    # Walk backwards to find JSON object candidates
    candidates: list[str] = []
    i = len(tail) - 1
    while i >= 0:
        if tail[i] == "}":
            depth = 0
            end = i
            j = i
            while j >= 0:
                ch = tail[j]
                if ch == "}":
                    depth += 1
                elif ch == "{":
                    depth -= 1
                    if depth == 0:
                        candidates.append(tail[j : end + 1])
                        break
                j -= 1
            i = j - 1
        else:
            i -= 1
        if len(candidates) >= 5:
            break

    for candidate in candidates:
        data = _try_parse_json(candidate)
        if data is not None and _validate_stage_output(data) is not None:
            return data

    return None


def extract_envelope(text: str) -> tuple[StageOutput | None, str | None]:
    """Extract a structured output envelope from agent result text.

    Finds `<pixl_output>{JSON}</pixl_output>` markers. If multiple
    envelopes exist, uses the **last** one (agents may include examples
    before the real output).

    Repair strategies (in order): regex sanitization → json-repair →
    XML-like coercion.  Every candidate is validated against the
    ``StageOutput`` model before acceptance.

    Args:
        text: Full agent result text.

    Returns:
        Tuple of (stage_output, error_message):
        - (StageOutput, None) on success
        - (None, error_msg) on parse/validation failure
        - (None, None) if no envelope found
    """
    matches = _ENVELOPE_RE.findall(text)
    if not matches:
        # Fallback: scan for bare JSON with stage_id
        fallback_data = _extract_fallback_json(text)
        if fallback_data is not None:
            stage_output = _validate_stage_output(fallback_data)
            if stage_output is not None:
                return stage_output, None
            return None, "Found JSON but StageOutput validation failed"
        return None, None

    # Use last match
    json_str = matches[-1].strip()

    # Try parsing (json.loads → sanitize → json-repair)
    data = _try_parse_json(json_str)

    if data is not None:
        stage_output = _validate_stage_output(data)
        if stage_output is not None:
            return stage_output, None

    # Fall back to XML-like coercion
    coerced = _coerce_xml_like_envelope(json_str)
    if coerced is not None:
        stage_output = _validate_stage_output(coerced)
        if stage_output is not None:
            return stage_output, None

    # Nothing worked — report what went wrong
    if data is not None:
        return None, "StageOutput validation failed"
    return None, "Invalid JSON in <pixl_output> envelope"


__all__ = ["extract_envelope"]
