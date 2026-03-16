"""Codex provider wrapping the OpenAI Codex CLI.

This provider uses the `codex exec` CLI command for non-interactive
execution. Codex is a terminal-based AI coding assistant from OpenAI.

Key details:
- Uses CLI tool: `codex exec` (installed via `npm i -g @openai/codex`)
- Authentication: CODEX_API_KEY environment variable
- Output: JSON Lines format with --json flag
- Documentation: https://developers.openai.com/codex/noninteractive/

Note: This provider wraps the CLI tool since Codex does not have a
public Python SDK. The CLI handles all model selection and execution.
"""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Any, ClassVar

from pixl.models.usage_limits import ProviderUsageLimits
from pixl.providers.auth import AuthResolver
from pixl.providers.base import LLMProvider, ProviderCapabilities
from pixl.providers.chunk_types import (
    error_chunk,
    file_change_chunk,
    progress_chunk,
    text_chunk,
    thinking_chunk,
    tool_call_chunk,
    turn_end_chunk,
)
from pixl.providers.rate_limits import parse_int, parse_reset_ms

class CodexProvider(LLMProvider):
    """Codex provider wrapping the OpenAI Codex CLI tool.

    Uses `codex exec` for non-interactive execution with JSON output.
    """

    # Model aliases for Codex CLI selection.
    MODEL_ALIASES: ClassVar[dict[str, str]] = {
        "codex": "default",
        "codex-5.2": "gpt-5.2-codex",
        "spark": "gpt-5.3-codex:spark",
        "gpt4": "default",
    }

    VALID_MODELS: ClassVar[set[str]] = {"default", "gpt-5.2-codex"}
    _REASONING_EFFORT_ALIASES: ClassVar[dict[str, str]] = {
        "spark": "high",
    }
    _VALID_REASONING_EFFORTS: ClassVar[set[str]] = {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    }

    def __init__(self) -> None:
        self._auth_resolver = AuthResolver()

    @property
    def name(self) -> str:
        return "codex"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=True,  # Codex has tool access via CLI
            supports_vision=True,
            supports_function_calling=True,
            max_context_tokens=128000,  # Codex supports large context
            max_output_tokens=8192,
            is_agentic=True,  # Codex CLI runs its own agent loop
        )

    def validate_model(self, model: str) -> bool:
        """Codex CLI handles model selection internally."""
        return True

    def resolve_alias(self, model: str) -> str:
        """Resolve a model alias to full model name for Codex CLI."""
        return self.MODEL_ALIASES.get(model, model)

    def _parse_model_and_effort(self, model: str | None) -> tuple[str | None, str | None]:
        """Extract model name and reasoning effort from a model string.

        Supports:
        - "gpt-5.2-codex"
        - "gpt-5.2-codex:xhigh" (or "@xhigh")
        - "spark" (alias for gpt-5.3-codex:spark)
        - "codex-5.2" (alias → gpt-5.2-codex)
        """
        if not model:
            return None, None

        effort: str | None = None
        base = model
        if ":" in model:
            base, effort = model.split(":", 1)
        elif "@" in model:
            base, effort = model.split("@", 1)

        base = base.strip()
        effort = effort.strip().lower() if effort else None

        # Resolve aliases (e.g., codex-5.2 → gpt-5.2-codex)
        base = self.MODEL_ALIASES.get(base, base)

        # Normalize model reasoning effort aliases. The Codex CLI expects
        # reasoning levels from the fixed enum set; map custom aliases.
        if effort:
            effort = self._REASONING_EFFORT_ALIASES.get(effort, effort)
            if effort not in self._VALID_REASONING_EFFORTS:
                effort = None

        return base, effort

    async def query(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Query Codex via the CLI tool.

        Args:
            prompt: User prompt
            model: Not used (Codex CLI handles model selection)
            system_prompt: Optional system prompt (prepended to prompt)
            tools: Not used (Codex has built-in tool access)
            **kwargs: Additional options. Supports:
                - full_auto: Allow edits without approval (default: False)
                - sandbox: Sandbox mode (default: "read-only")
                - json_output: Return JSON Lines format (default: True)

        Returns:
            AsyncIterator yielding response chunks from Codex CLI
        """
        try:
            import shutil

            if not shutil.which("codex"):
                yield error_chunk(
                    "Codex CLI not found. Install with: npm i -g @openai/codex",
                )
                return
        except Exception:
            yield error_chunk(
                "Could not check for Codex CLI installation",
            )
            return

        cmd = ["codex", "exec", "--json"]

        sandbox = kwargs.get("sandbox", "read-only")
        cmd.extend(["--sandbox", sandbox])

        if kwargs.get("full_auto", False):
            cmd.append("--full-auto")

        # Avoid hard git repo trust checks for non-interactive API execution.
        # Codex defaults to requiring trusted directories; this can fail when
        # Pixl invokes the CLI from ephemeral worktrees.
        if kwargs.get("skip_git_repo_check", True):
            cmd.append("--skip-git-repo-check")

        # Add extra writable directories (e.g. session artifacts dir)
        for extra_dir in kwargs.get("extra_writable_dirs", []):
            cmd.extend(["--add-dir", extra_dir])

        model_name, reasoning_effort = self._parse_model_and_effort(model)
        if model_name and model_name != "default":
            cmd.extend(["--model", model_name])
        if reasoning_effort:
            cmd.extend(["--config", f'model_reasoning_effort="{reasoning_effort}"'])

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        cmd.append(full_prompt)

        # The Codex CLI manages its own auth via ~/.codex/auth.json,
        # so we only inject an explicit key if one is provided -- we
        # never block execution just because no env-var key was found.
        env = os.environ.copy()

        # Only try to inject API key if explicitly set
        # Don't use AuthResolver.is_valid since CLI OAuth is valid too
        api_key = os.getenv("CODEX_API_KEY")
        if api_key:
            env["CODEX_API_KEY"] = api_key

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=4 * 1024 * 1024,  # 4 MB — Codex can emit large JSON lines
                env=env,
                cwd=kwargs.get("cwd", os.getcwd()),
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()
                if not line_str:
                    continue

                try:
                    event = json.loads(line_str)
                    event_type = event.get("type")

                    # Stream different event types
                    if event_type == "thread.started":
                        yield {"type": "start", "thread_id": event.get("thread_id")}

                    elif event_type == "turn.started":
                        yield {"type": "turn_start"}

                    elif event_type == "item.completed":
                        item = event.get("item", {})
                        item_type = item.get("type", "")

                        if item_type == "agent_message":
                            text = item.get("text", "")
                            if text:
                                yield text_chunk(text)

                        elif item_type == "command_execution":
                            yield tool_call_chunk(
                                "Bash",
                                {"command": item.get("command", "")},
                                output=item.get("output", ""),
                                exit_code=item.get("exit_code"),
                            )

                        elif item_type in ("file_edit", "file_create"):
                            yield file_change_chunk(
                                item_type,
                                item.get("path", item.get("file_path", "")),
                                diff=item.get("diff", ""),
                            )

                        elif item_type == "file_read":
                            yield tool_call_chunk(
                                "Read",
                                {"file_path": item.get("path", item.get("file_path", ""))},
                            )

                        elif item_type == "reasoning":
                            content = item.get("text", item.get("content", ""))
                            if content:
                                yield thinking_chunk(content)

                        else:
                            # Unknown item type -- yield any text
                            text = item.get("text", "")
                            if text:
                                yield text_chunk(text)

                    elif event_type == "item.started":
                        item = event.get("item", {})
                        if item.get("type") == "command_execution":
                            yield progress_chunk(
                                f"Running: {item.get('command', '')[:80]}",
                            )

                    elif event_type == "turn.completed":
                        yield turn_end_chunk(event.get("usage", {}))

                    elif event_type == "error":
                        yield error_chunk(event.get("message", "Unknown error"))

                except json.JSONDecodeError:
                    # Non-JSON output, treat as text
                    if line_str:
                        yield text_chunk(line_str)

            # Wait for process to complete
            await process.wait()

            if process.returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode().strip()
                if error_msg:
                    yield error_chunk(f"Codex CLI error: {error_msg}")

        except FileNotFoundError:
            yield error_chunk(
                "Codex CLI not found. Install with: npm i -g @openai/codex",
            )
        except Exception as e:
            yield error_chunk(
                f"Codex execution error: {e!s}",
            )

    async def get_usage_limits(self) -> ProviderUsageLimits:
        """Get current rate limits from OpenAI API.

        Uses the openai SDK with raw response access to get rate limit headers.
        Codex uses OpenAI's API, so we query OpenAI directly.

        Returns:
            ProviderUsageLimits with current limits
        """
        try:
            import openai
        except ImportError:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error="openai package not installed. Install with: pip install openai",
            )

        auth_result = self._auth_resolver.resolve("codex")

        if not auth_result.is_valid:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error="Codex authentication not configured. Set CODEX_API_KEY or use OAuth.",
            )

        try:
            client = openai.OpenAI(api_key=auth_result.token)

            # Make minimal request to get headers
            response = client.chat.completions.with_raw_response.create(
                model="gpt-4o-mini",  # Use cheapest model
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )

            headers = response.headers

            return ProviderUsageLimits(
                provider=self.name,
                model="gpt-4o-mini",
                # Request limits
                requests_limit=parse_int(headers.get("x-ratelimit-limit-requests")),
                requests_remaining=parse_int(headers.get("x-ratelimit-remaining-requests")),
                requests_reset=parse_reset_ms(headers.get("x-ratelimit-reset-requests")),
                # Token limits
                input_tokens_limit=parse_int(headers.get("x-ratelimit-limit-tokens")),
                input_tokens_remaining=parse_int(headers.get("x-ratelimit-remaining-tokens")),
                tokens_reset=parse_reset_ms(headers.get("x-ratelimit-reset-tokens")),
                available=True,
            )

        except openai.AuthenticationError:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error="Invalid API key. Set CODEX_API_KEY environment variable.",
            )
        except openai.APIError as e:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error=f"OpenAI API error: {e!s}",
            )
        except Exception as e:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error=f"Failed to fetch limits: {e!s}",
            )

__all__ = ["CodexProvider"]
