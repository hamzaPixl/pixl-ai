"""Anthropic provider using Claude Code SDK."""

from collections.abc import AsyncIterator
from typing import Any, ClassVar, Literal

from claude_agent_sdk import ClaudeAgentOptions, query

from pixl.agents.constants import DEFAULT_TOOLS
from pixl.models.usage_limits import ProviderUsageLimits
from pixl.providers.auth import AuthResolver
from pixl.providers.base import LLMProvider, ProviderCapabilities
from pixl.providers.rate_limits import parse_int, parse_reset_iso

PermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]

class AnthropicProvider(LLMProvider):
    """Anthropic provider wrapping Claude Code SDK.

    Uses the Claude Code SDK for all interactions, which handles
    authentication automatically via environment variables.
    """

    MODEL_ALIASES: ClassVar[dict[str, str]] = {
        "opus": "claude-opus-4-6",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5",
        "glm": "glm-5",
    }

    VALID_MODELS: ClassVar[set[str]] = {
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "glm-5",
    }

    def __init__(self) -> None:
        # AuthResolver is instantiated for future use when we add support for
        # custom API key management and authentication strategies. Currently,
        # the Claude Code SDK handles authentication automatically via env vars.
        self._auth_resolver = AuthResolver()

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            supports_function_calling=True,
            max_context_tokens=200000,
            max_output_tokens=8192,
        )

    def validate_model(self, model: str) -> bool:
        """Check if a model is valid for Anthropic."""
        resolved = self.resolve_alias(model)
        return resolved in self.VALID_MODELS

    def resolve_alias(self, model: str) -> str:
        """Resolve a model alias to full model name."""
        return self.MODEL_ALIASES.get(model, model)

    async def query(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Query Claude via the SDK.

        Args:
            prompt: User prompt
            model: Model to use (alias or full name)
            system_prompt: System prompt
            tools: Tool definitions (unused - SDK handles tools)
            **kwargs: Additional options. Supports:
                - cwd: Working directory
                - allowed_tools: Tools to allow
                - permission_mode: Permission mode (default, acceptEdits, plan, bypassPermissions)
                - max_turns: Maximum turns

        Returns:
            AsyncIterator yielding response chunks from SDK
        """
        resolved_model = self.resolve_alias(model) if model else None

        cwd: str | None = kwargs.get("cwd")
        allowed_tools: list[str] | None = kwargs.get("allowed_tools")
        permission_mode: PermissionMode = kwargs.get("permission_mode", "bypassPermissions")
        max_turns: int = kwargs.get("max_turns", 50)

        # Extended thinking and effort (SDK v0.1.37+)
        thinking = kwargs.get("thinking")
        effort = kwargs.get("effort")

        if thinking is not None:
            from pixl.agents.sdk_options import resolve_thinking_config

            thinking = resolve_thinking_config(thinking)

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=allowed_tools or list(DEFAULT_TOOLS),
            permission_mode=permission_mode,
            cwd=cwd,
            max_turns=max_turns,
            model=resolved_model,
            setting_sources=["user", "project"],
            thinking=thinking,
            effort=effort,
        )

        async def _generate() -> AsyncIterator[dict[str, Any]]:
            async for message in query(prompt=prompt, options=options):
                yield self._convert_message(message)

        return _generate()

    def _convert_message(self, message: Any) -> dict[str, Any]:
        """Convert SDK message to standard format."""
        # The SDK returns various message types
        if hasattr(message, "model_dump"):
            result: dict[str, Any] = message.model_dump()
            return result
        elif hasattr(message, "__dict__"):
            result = dict(message.__dict__)
            return result
        return {"content": str(message)}

    async def get_usage_limits(self) -> ProviderUsageLimits:
        """Get current rate limits from Anthropic API.

        Makes a minimal API call to retrieve rate limit headers.
        Uses the anthropic SDK with raw response access.

        Returns:
            ProviderUsageLimits with current limits
        """
        import os

        try:
            import anthropic
        except ImportError:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error="anthropic package not installed",
            )

        # Use AuthResolver to get the token
        auth_result = self._auth_resolver.resolve("anthropic")
        if not auth_result.is_valid:
            if os.environ.get("CLAUDECODE") == "1":
                return ProviderUsageLimits(
                    provider=self.name,
                    available=False,
                    error=(
                        "Claude Code subscription auth detected."
                        " Usage limits require OAuth credentials."
                    ),
                )
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error=(
                    "Anthropic authentication not configured."
                    " Ensure OAuth credentials are available."
                ),
            )

        try:
            # Pass the token to the client
            client = anthropic.Anthropic(api_key=auth_result.token)

            # Make minimal request to get headers
            response = client.messages.with_raw_response.create(
                model="claude-haiku-4-5",  # Use cheapest model
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )

            headers = response.headers

            return ProviderUsageLimits(
                provider=self.name,
                model="claude-haiku-4-5",
                # Request limits
                requests_limit=parse_int(headers.get("anthropic-ratelimit-requests-limit")),
                requests_remaining=parse_int(headers.get("anthropic-ratelimit-requests-remaining")),
                requests_reset=parse_reset_iso(headers.get("anthropic-ratelimit-requests-reset")),
                # Token limits (Anthropic combines input+output)
                input_tokens_limit=parse_int(headers.get("anthropic-ratelimit-tokens-limit")),
                input_tokens_remaining=parse_int(
                    headers.get("anthropic-ratelimit-tokens-remaining")
                ),
                tokens_reset=parse_reset_iso(headers.get("anthropic-ratelimit-tokens-reset")),
                available=True,
            )

        except anthropic.AuthenticationError:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error="Invalid API key. Ensure OAuth credentials are valid.",
            )
        except anthropic.APIError as e:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error=f"Anthropic API error: {e!s}",
            )
        except Exception as e:
            return ProviderUsageLimits(
                provider=self.name,
                available=False,
                error=f"Failed to fetch limits: {e!s}",
            )

