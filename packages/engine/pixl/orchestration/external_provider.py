"""External (non-Anthropic) provider integration for orchestrator queries.

Extracted from core.py — handles routing queries to external providers,
usage normalization, skill context injection, and stream message construction.
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _dedup_json
import logging
import time as _time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from pixl.config.providers import ProvidersConfig
from pixl.models.event import Event
from pixl.output import console, is_json_mode
from pixl.providers import ProviderRegistry

# Lightweight duck-typed message blocks for stream callbacks

class _TextBlock:
    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text

class _ToolCallBlock:
    __slots__ = ("name", "input")

    def __init__(self, name: str, tool_input: dict[str, Any]) -> None:
        self.name = name
        self.input = tool_input

class _ThinkingBlock:
    __slots__ = ("thinking",)

    def __init__(self, text: str) -> None:
        self.thinking = text

class _StreamMessage:
    __slots__ = ("content",)

    def __init__(self, blocks: list) -> None:
        self.content = blocks

# Message factory helpers

def make_text_message(text: str) -> Any:
    """Create a duck-typed message object compatible with stream callbacks."""
    return _StreamMessage([_TextBlock(text)])

def make_tool_call_message(tool_name: str, tool_input: dict[str, Any]) -> Any:
    """Create a duck-typed tool-call message for stream callbacks."""
    return _StreamMessage([_ToolCallBlock(tool_name, tool_input)])

def make_thinking_message(content: str) -> Any:
    """Create a duck-typed thinking message for stream callbacks."""
    return _StreamMessage([_ThinkingBlock(content)])

# Utility helpers

def truncate_tool_input(tool_input: dict[str, Any], limit: int = 500) -> dict[str, Any]:
    """Truncate string values in a tool input dict for event payloads."""
    return {
        k: (v[:limit] + "..." if isinstance(v, str) and len(v) > limit else v)
        for k, v in tool_input.items()
    }

def normalize_external_usage(raw_usage: dict[str, Any]) -> dict[str, Any]:
    """Normalize external-provider usage payloads to common token keys."""

    def _num(value: Any) -> int | float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return None
        return None

    input_candidates = (
        "input_tokens",
        "prompt_tokens",
        "input_token_count",
        "prompt_token_count",
    )
    output_candidates = (
        "output_tokens",
        "completion_tokens",
        "output_token_count",
        "completion_token_count",
    )
    total_candidates = ("total_tokens", "total_token_count")
    cost_candidates = ("cost_usd", "total_cost_usd", "cost")

    def _first_numeric(keys: tuple[str, ...]) -> int | float | None:
        for key in keys:
            if key in raw_usage:
                parsed = _num(raw_usage.get(key))
                if parsed is not None:
                    return parsed
        return None

    normalized = dict(raw_usage)

    input_tokens = _first_numeric(input_candidates)
    output_tokens = _first_numeric(output_candidates)
    total_tokens = _first_numeric(total_candidates)
    cost_usd = _first_numeric(cost_candidates)

    if input_tokens is not None:
        normalized["input_tokens"] = int(input_tokens)
    if output_tokens is not None:
        normalized["output_tokens"] = int(output_tokens)
    if total_tokens is not None:
        normalized["total_tokens"] = int(total_tokens)
    elif input_tokens is not None and output_tokens is not None:
        normalized["total_tokens"] = int(input_tokens + output_tokens)
    if cost_usd is not None:
        normalized["cost_usd"] = float(cost_usd)

    return normalized

# Provider helpers

def get_provider_name(providers_config: ProvidersConfig, model: str) -> str:
    """Extract provider name from a model string."""
    provider_name, _ = providers_config.parse_model_string(model)
    return provider_name

def is_sdk_provider(providers_config: ProvidersConfig, model: str, sdk_providers: set[str]) -> bool:
    """Check if a model string maps to a provider using claude_agent_sdk."""
    return get_provider_name(providers_config, model) in sdk_providers

# External provider query

async def query_external_provider(
    prompt: str,
    model: str,
    *,
    providers_config: ProvidersConfig,
    provider_registry: ProviderRegistry,
    project_path: Path,
    stream_callback: Callable[[Any], None] | None = None,
    workflow_tags: list[str] | None = None,
    stage_id: str | None = None,
    agent_name: str | None = None,
    extra_writable_dirs: list[str] | None = None,
    emit_sdk_event: Callable[[Event], None] | None = None,
    sdk_session_id: str | None = None,
    sdk_node_id: str | None = None,
    cwd: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    """Route a query to a non-Anthropic provider."""
    provider_name, model_name = providers_config.parse_model_string(model)
    provider = provider_registry.get(provider_name)
    is_agentic = provider.capabilities.is_agentic

    if is_agentic:
        console.info(f"External provider '{provider_name}' — agentic mode (tool use enabled)")
    else:
        console.warning(f"External provider '{provider_name}' — text generation only (no tool use)")

    working_dir = str(cwd) if cwd else str(project_path)
    kwargs: dict[str, Any] = {"cwd": working_dir}
    if is_agentic:
        kwargs["full_auto"] = True
        if extra_writable_dirs:
            kwargs["extra_writable_dirs"] = extra_writable_dirs

    result_iter = provider.query(prompt=prompt, model=model_name, **kwargs)
    if not hasattr(result_iter, "__aiter__"):
        result_iter = await result_iter

    text_parts: list[str] = []
    trace_chunks: list[dict[str, Any]] = []
    trace_segments: list[str] = []
    trace_char_count = 0
    trace_max_chars = 120_000
    trace_truncated = False
    usage_events: list[dict[str, Any]] = []
    usage: dict[str, Any] | None = None
    error_message: str | None = None

    def _emit(event: Event) -> None:
        if emit_sdk_event is not None:
            emit_sdk_event(event)

    def append_trace(segment: str | None) -> None:
        nonlocal trace_char_count, trace_truncated
        if not segment:
            return
        remaining = trace_max_chars - trace_char_count
        if remaining <= 0:
            trace_truncated = True
            return
        clipped = segment[:remaining]
        trace_segments.append(clipped)
        trace_char_count += len(clipped)
        if len(clipped) < len(segment):
            trace_truncated = True

    sess = sdk_session_id or ""
    node = sdk_node_id or ""

    _ext_start = _time.monotonic()

    _emit(Event.sdk_query_started(sess, node, model_name, prompt_preview=prompt[:200]))

    _prev_tool_key: str | None = None
    _prev_tool_time: float = 0.0
    _tool_dedup_window = 2.0

    provider_session_id: str | None = None

    async for chunk in result_iter:
        chunk_type = chunk.get("type", "")
        content = chunk.get("content", "")

        if chunk_type == "text" and content:
            text_parts.append(content)
            if stream_callback:
                stream_callback(make_text_message(content))
            elif not is_json_mode():
                console.stream_text(content)
            _emit(
                Event.sdk_text_delta(
                    sess,
                    node,
                    content[:500] if len(content) > 500 else content,
                )
            )

        elif chunk_type == "tool_call":
            tool_name = str(chunk.get("tool_name", "Tool"))
            tool_input = chunk.get("tool_input", {})
            if not isinstance(tool_input, dict):
                tool_input = {"value": tool_input}
            output = chunk.get("output", "")

            trace_chunk: dict[str, Any] = {
                "type": "tool_call",
                "tool_name": tool_name,
                "tool_input": tool_input,
            }
            if output:
                trace_chunk["output"] = output
                append_trace(str(output))
            if chunk.get("exit_code") is not None:
                trace_chunk["exit_code"] = chunk.get("exit_code")
            trace_chunks.append(trace_chunk)

            _tool_key = (
                f"{tool_name}:"
                f"{_hashlib.md5(_dedup_json.dumps(tool_input, sort_keys=True).encode()).hexdigest()}"
            )
            _now = _time.monotonic()
            _is_dup = _tool_key == _prev_tool_key and _now - _prev_tool_time < _tool_dedup_window
            _prev_tool_key = _tool_key
            _prev_tool_time = _now

            if not _is_dup:
                _emit(
                    Event.sdk_tool_call_started(
                        sess, node, tool_name, truncate_tool_input(tool_input)
                    )
                )
                exit_code = chunk.get("exit_code")
                is_err = exit_code is not None and exit_code != 0
                _emit(Event.sdk_tool_call_completed(sess, node, tool_name, is_error=is_err))

                if stream_callback:
                    stream_callback(make_tool_call_message(tool_name, tool_input))
                elif not is_json_mode():
                    console.stream_tool_call(tool_name, tool_input)

        elif chunk_type == "file_change":
            change = str(chunk.get("change_type", "file_edit"))
            file_path = str(chunk.get("file_path", ""))
            diff = chunk.get("diff", "")

            trace_chunk = {
                "type": "file_change",
                "change_type": change,
                "file_path": file_path,
            }
            if diff:
                trace_chunk["diff"] = diff
            trace_chunks.append(trace_chunk)

            tool_name = "Write" if change == "file_create" else "Edit"
            tool_input = {"file_path": file_path}
            _emit(Event.sdk_tool_call_started(sess, node, tool_name, tool_input))
            _emit(Event.sdk_tool_call_completed(sess, node, tool_name))

            if stream_callback:
                stream_callback(make_tool_call_message(tool_name, tool_input))
            elif not is_json_mode():
                console.stream_tool_call(tool_name, tool_input)

        elif chunk_type == "thinking":
            if content:
                trace_chunks.append({"type": "thinking", "content": content})
                append_trace(str(content))
                _emit(Event.sdk_thinking_started(sess, node))
                if stream_callback:
                    stream_callback(make_thinking_message(str(content)))
                elif not is_json_mode():
                    console.stream_thinking(str(content))

        elif chunk_type == "progress":
            message = chunk.get("message")
            if message:
                trace_chunks.append({"type": "progress", "message": message})
                if not is_json_mode() and stream_callback is None:
                    console.meta(f"  {message}")

        elif chunk_type == "turn_end":
            raw_usage = chunk.get("usage")
            if isinstance(raw_usage, dict) and raw_usage:
                usage = normalize_external_usage(raw_usage)
                usage_events.append(usage)

        elif chunk_type == "error":
            error_message = str(content) if content else "Unknown provider error"
            trace_chunks.append({"type": "error", "content": error_message})
            break

        elif chunk_type == "gemini_session":
            provider_session_id = chunk.get("session_id")

    _ext_duration = _time.monotonic() - _ext_start
    _emit(Event.sdk_query_completed(sess, node, _ext_duration, usage=usage))

    if error_message:
        raise RuntimeError(error_message)

    metadata: dict[str, Any] = {
        "success": True,
        "provider": provider_name,
        "is_agentic": is_agentic,
        "trace_chunks": trace_chunks,
        "trace_text": "\n\n".join(trace_segments),
        "trace_truncated": trace_truncated,
    }
    if usage:
        metadata["usage"] = usage
        metadata["usage_events"] = usage_events
    if provider_session_id:
        metadata["provider_session_id"] = provider_session_id
    return "".join(text_parts), metadata
