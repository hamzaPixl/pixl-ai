"""Gemini provider wrapping the Google Gemini CLI.

This provider delegates all subprocess management to
:class:`~pixl.providers.gemini.client.GeminiCLIClient` and converts
typed :class:`~pixl.providers.gemini.models.GeminiEvent` instances into
the Pixl chunk protocol consumed by ``external_provider.py``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, ClassVar

from pixl.models.usage_limits import ProviderUsageLimits
from pixl.providers.base import LLMProvider, ProviderCapabilities
from pixl.providers.chunk_types import (
    error_chunk,
    progress_chunk,
    text_chunk,
    tool_call_chunk,
    turn_end_chunk,
)
from pixl.providers.gemini.client import (
    CLINotFoundError,
    GeminiCLIClient,
    OAuthNotConfiguredError,
)
from pixl.providers.gemini.models import (
    ErrorEvent,
    InitEvent,
    MessageEvent,
    ResultEvent,
    ToolResultEvent,
    ToolUseEvent,
)
from pixl.providers.gemini.parser import extract_usage_from_stream_stats

logger = logging.getLogger(__name__)

_GEMINI_ARTIFACT_INSTRUCTIONS = """\
## CRITICAL: Saving Artifacts (Gemini-specific)

You MUST use your `run_shell_command` tool to call `pixl artifact put` for every
file you create or modify that should be tracked as a workflow artifact.
Use `--file` to avoid shell expansion issues with special characters:

```
run_shell_command(command="pixl artifact put --name plan.md --file plan.md")
```

Use `--json` for machine-readable output:
```
run_shell_command(command="pixl artifact put --name plan.md --file plan.md --json")
# Returns: {"name": "plan.md", "session_id": "...", "sha256": "..."}
```

DO NOT use `--content "$(cat ...)"` — this corrupts content with special characters.
Only `pixl artifact put` persists artifacts to the session store. Validation will
FAIL if you skip this step.

## CRITICAL: Structured Stage Output

When completing a stage, you MUST register the structured output via
`pixl artifact stage-output`. Write your StageOutput JSON to a file, then:

```
run_shell_command(command="pixl artifact stage-output --file /tmp/stage_output.json")
```

The JSON must conform to the StageOutput schema (stage_id, status, summary, etc.).
"""


class GeminiProvider(LLMProvider):
    """Gemini provider wrapping the Gemini CLI tool.

    Uses :class:`GeminiCLIClient` for subprocess management and streams
    typed events, converting them to the Pixl chunk protocol.
    """

    MODEL_ALIASES: ClassVar[dict[str, str]] = {
        "default": "gemini-3-pro-preview",
    }

    def __init__(self) -> None:
        self._client = GeminiCLIClient()

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            supports_function_calling=True,
            max_context_tokens=128000,
            max_output_tokens=8192,
            is_agentic=True,
        )

    def validate_model(self, model: str) -> bool:
        """Gemini CLI handles model validation and routing."""
        return True

    def resolve_alias(self, model: str) -> str:
        """Resolve a model alias to a concrete Gemini model name."""
        return self.MODEL_ALIASES.get(model, model)

    # Query — converts GeminiEvent → Pixl chunks

    async def query(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Query Gemini via the CLI tool."""
        resolved_model = self.resolve_alias(model) if model else None

        full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"

        # Inject artifact instructions when relevant
        _ = tools  # Gemini CLI handles tool access internally.
        _artifact_keywords = ("artifact", "pixl artifact put", "artifacts_written")
        if any(kw in full_prompt.lower() for kw in _artifact_keywords):
            full_prompt = _GEMINI_ARTIFACT_INSTRUCTIONS + "\n\n" + full_prompt

        full_auto = bool(kwargs.get("full_auto", False))
        extra_writable_dirs = list(kwargs.get("extra_writable_dirs", []))
        cwd = kwargs.get("cwd") or None

        # Tool-call correlation: track tool_use → tool_result pairing
        tool_calls: dict[str, tuple[str, dict[str, Any]]] = {}

        # Track CLI session ID for resume support
        cli_session_id: str | None = None
        resume_session_id = kwargs.get("resume_session_id") or None
        # Track whether we already emitted text from message events
        # to avoid duplicate text from result.text
        has_streamed_text = False

        try:
            async for event in self._client.query(
                full_prompt,
                model=resolved_model,
                cwd=str(cwd) if cwd else None,
                yolo=full_auto,
                extra_dirs=extra_writable_dirs,
                resume_session_id=resume_session_id,
            ):
                for chunk in self._event_to_chunks(event, tool_calls):
                    if chunk.get("type") == "text":
                        has_streamed_text = True
                    yield chunk

                # Emit result.text ONLY if no prior text was streamed
                # (avoids duplicating text already sent via message events)
                if isinstance(event, ResultEvent) and event.text and not has_streamed_text:
                    yield text_chunk(event.text)

                # Capture session ID from init event
                if isinstance(event, InitEvent) and event.session_id:
                    cli_session_id = event.session_id

        except CLINotFoundError as exc:
            yield error_chunk(str(exc))
        except OAuthNotConfiguredError as exc:
            yield error_chunk(str(exc))
        except Exception as exc:
            yield error_chunk(f"Gemini execution error: {exc!s}")

        if cli_session_id:
            yield {"type": "gemini_session", "session_id": cli_session_id}

    # Event → Chunk mapping

    @staticmethod
    def _event_to_chunks(
        event: Any,
        tool_calls: dict[str, tuple[str, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Convert a typed GeminiEvent into Pixl chunk dicts."""
        chunks: list[dict[str, Any]] = []

        if isinstance(event, MessageEvent):
            if event.role == "assistant" and event.content:
                chunks.append(text_chunk(event.content))

        elif isinstance(event, ToolUseEvent):
            # Do NOT emit a chunk here — ToolResultEvent emits the single
            # tool_call chunk with complete output + exit_code.
            if event.tool_id:
                tool_calls[event.tool_id] = (event.tool_name, event.parameters)

        elif isinstance(event, ToolResultEvent):
            default_input: dict[str, Any] = {"tool_id": event.tool_id} if event.tool_id else {}
            tool_name, tool_input = tool_calls.get(event.tool_id, ("Tool", default_input))

            output = ""
            if isinstance(event.output, str) and event.output:
                output = event.output

            exit_code: int | None = None
            if event.status:
                exit_code = 0 if event.status == "success" else 1

            if event.status != "success" and event.error:
                if isinstance(event.error, dict):
                    err_msg = str(event.error.get("message", ""))
                else:
                    err_msg = str(event.error)
                if err_msg:
                    output = f"{output}\n{err_msg}".strip()

            chunks.append(
                tool_call_chunk(tool_name, tool_input, output=output, exit_code=exit_code)
            )

        elif isinstance(event, ErrorEvent):
            severity = event.severity.lower() if event.severity else "error"
            if severity == "warning":
                chunks.append(progress_chunk(event.message))
            else:
                chunks.append(error_chunk(event.message))

        elif isinstance(event, ResultEvent):
            if event.status == "success":
                usage = extract_usage_from_stream_stats(event.stats)
                if usage:
                    chunks.append(turn_end_chunk(usage))
            elif event.status == "error":
                err = event.error
                if isinstance(err, dict):
                    message = str(err.get("message", "Unknown Gemini error"))
                else:
                    message = str(err) if err is not None else "Unknown Gemini error"
                chunks.append(error_chunk(message))

        return chunks

    # Usage limits

    async def get_usage_limits(self) -> ProviderUsageLimits:
        """Gemini CLI OAuth mode does not expose usage limits."""
        return ProviderUsageLimits(
            provider=self.name,
            available=False,
            error="Usage limits are not implemented for Gemini CLI provider.",
        )


__all__ = ["GeminiProvider"]
