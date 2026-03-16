"""Authentication resolver for LLM providers.

Auth hierarchy (highest priority first):
1. Claude Code OAuth (CLAUDE_CODE_OAUTH_TOKEN) - when running in Claude Code
2. Codex SDK auth (CODEX_AUTH_TOKEN) - when running in Codex environment
3. Claude SDK sub auth (CLAUDE_SUB_AUTH_TOKEN) - delegated auth token
4. Anthropic auth token (ANTHROPIC_AUTH_TOKEN) - alternative API key format
5. Docker default auth (PIXL_DOCKER_AUTO_AUTH=true) - auto mode in containers
6. CLI OAuth files for external providers (Codex, Gemini)
"""

import os
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, Field


class AuthMethod(StrEnum):
    """Authentication method used."""

    CLAUDE_CODE_OAUTH = "claude_code_oauth"
    CODEX_SDK = "codex_sdk"
    CLAUDE_SDK_SUB = "claude_sdk_sub"
    ANTHROPIC_AUTH = "anthropic_auth"
    API_KEY = "api_key"
    DOCKER_DEFAULT = "docker_default"
    NONE = "none"


class AuthResult(BaseModel):
    """Result of authentication resolution."""

    method: AuthMethod
    token: str | None = None
    provider: str
    is_valid: bool = Field(default=False)
    _cli_auth_override: bool = False  # Internal: CLI has its own auth

    def model_post_init(self, __context: object) -> None:
        """Compute is_valid based on method and token."""
        if self.method == AuthMethod.NONE:
            object.__setattr__(self, "is_valid", False)
        elif self.method == AuthMethod.DOCKER_DEFAULT or self._cli_auth_override:
            object.__setattr__(self, "is_valid", True)
        else:
            object.__setattr__(self, "is_valid", self.token is not None)


class AuthResolver:
    """Resolves authentication for LLM providers.

    Hierarchy (highest priority first):
    1. CODEX_AUTH_TOKEN - Codex SDK environment
    2. CLAUDE_SUB_AUTH_TOKEN - Claude SDK delegated auth
    3. PIXL_DOCKER_AUTO_AUTH=true - Docker auto mode
    4. Codex CLI OAuth file (~/.codex/auth.json) - for codex provider only
    5. Gemini CLI OAuth file (~/.gemini/oauth_creds.json) - for gemini provider only
    """

    PROVIDER_API_KEY_ENV: ClassVar[dict[str, str]] = {}

    # Alternative env vars to check if primary is not set
    ALT_API_KEY_ENV: ClassVar[dict[str, list[str]]] = {}

    @staticmethod
    def _has_codex_cli_auth() -> bool:
        """Check if Codex CLI has OAuth configured."""
        auth_file = os.path.expanduser("~/.codex/auth.json")
        return os.path.exists(auth_file)

    @staticmethod
    def _has_gemini_cli_auth() -> bool:
        """Check if Gemini CLI has OAuth configured."""
        auth_file = os.path.expanduser("~/.gemini/oauth_creds.json")
        return os.path.exists(auth_file)

    @staticmethod
    def _build_cli_oauth_result(provider: str) -> AuthResult:
        """Build an auth result for providers that handle OAuth in their CLI."""
        result = AuthResult(
            method=AuthMethod.API_KEY,
            token=None,
            provider=provider,
        )
        object.__setattr__(result, "_cli_auth_override", True)
        object.__setattr__(result, "is_valid", True)
        return result

    def resolve(self, provider: str) -> AuthResult:
        """Resolve authentication for a provider.

        Args:
            provider: Provider name (e.g., anthropic, codex, gemini)

        Returns:
            AuthResult with method, token, and validity
        """
        # 1. Claude Code OAuth (highest priority - when running in Claude Code)
        claude_code_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
        if claude_code_token:
            return AuthResult(
                method=AuthMethod.CLAUDE_CODE_OAUTH,
                token=claude_code_token,
                provider=provider,
            )

        # 2. Codex SDK auth
        codex_token = os.getenv("CODEX_AUTH_TOKEN")
        if codex_token:
            return AuthResult(
                method=AuthMethod.CODEX_SDK,
                token=codex_token,
                provider=provider,
            )

        # 3. Claude SDK sub auth
        claude_sub_token = os.getenv("CLAUDE_SUB_AUTH_TOKEN")
        if claude_sub_token:
            return AuthResult(
                method=AuthMethod.CLAUDE_SDK_SUB,
                token=claude_sub_token,
                provider=provider,
            )

        # 4. Anthropic auth token (alternative API key format)
        anthropic_auth = os.getenv("ANTHROPIC_AUTH_TOKEN")
        if anthropic_auth:
            return AuthResult(
                method=AuthMethod.ANTHROPIC_AUTH,
                token=anthropic_auth,
                provider=provider,
            )

        # 5. Provider-specific API key
        api_key_env = self.PROVIDER_API_KEY_ENV.get(provider)
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if api_key:
                return AuthResult(
                    method=AuthMethod.API_KEY,
                    token=api_key,
                    provider=provider,
                )

            # Check alternative env vars (provider-specific fallbacks)
            alt_envs = self.ALT_API_KEY_ENV.get(provider, [])
            for alt_env in alt_envs:
                alt_key = os.getenv(alt_env)
                if alt_key:
                    return AuthResult(
                        method=AuthMethod.API_KEY,
                        token=alt_key,
                        provider=provider,
                    )

        # 6. Docker default auth (auto mode)
        if os.getenv("PIXL_DOCKER_AUTO_AUTH", "").lower() == "true":
            return AuthResult(
                method=AuthMethod.DOCKER_DEFAULT,
                token=None,
                provider=provider,
            )

        # 7. Codex CLI OAuth (special case - CLI manages its own auth)
        if provider == "codex" and self._has_codex_cli_auth():
            return self._build_cli_oauth_result(provider)

        # 8. Gemini CLI OAuth (special case - CLI manages its own auth)
        if provider == "gemini" and self._has_gemini_cli_auth():
            return self._build_cli_oauth_result(provider)

        # No auth available
        return AuthResult(
            method=AuthMethod.NONE,
            token=None,
            provider=provider,
        )

    def get_headers(self, provider: str) -> dict[str, str]:
        """Get HTTP headers for authenticated requests.

        Args:
            provider: Provider name

        Returns:
            Dict of HTTP headers with auth
        """
        result = self.resolve(provider)

        if not result.is_valid:
            return {}
        if result._cli_auth_override:
            return {}

        if result.method == AuthMethod.CLAUDE_CODE_OAUTH:
            # Claude Code OAuth uses x-api-key header
            return {"x-api-key": result.token or ""}
        elif result.method == AuthMethod.CODEX_SDK:
            return {"Authorization": f"Bearer {result.token}"}
        elif result.method == AuthMethod.CLAUDE_SDK_SUB:
            return {"X-Claude-Sub-Auth": result.token or ""}
        elif result.method == AuthMethod.ANTHROPIC_AUTH:
            return {"x-api-key": result.token or ""}
        elif result.method == AuthMethod.API_KEY:
            return {"Authorization": result.token or ""}

        return {}
