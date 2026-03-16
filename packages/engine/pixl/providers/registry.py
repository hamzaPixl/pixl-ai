"""Provider registry for managing LLM providers."""

from typing import ClassVar

from pixl.providers.anthropic_provider import AnthropicProvider
from pixl.providers.base import LLMProvider
from pixl.providers.codex_provider import CodexProvider
from pixl.providers.gemini_provider import GeminiProvider


class ProviderRegistry:
    """Registry for managing LLM providers.

    Provides:
    - Provider lookup by name
    - Model string resolution (provider/model)
    - Validation of model strings
    """

    DEFAULT_PROVIDER: ClassVar[str] = "anthropic"

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default providers."""
        self.register(AnthropicProvider())
        self.register(CodexProvider())
        self.register(GeminiProvider())

    def register(self, provider: LLMProvider) -> None:
        """Register a provider."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> LLMProvider:
        """Get a provider by name.

        Args:
            name: Provider name

        Returns:
            LLMProvider instance

        Raises:
            KeyError: If provider not found
        """
        if name not in self._providers:
            raise KeyError(f"Unknown provider: {name}")
        return self._providers[name]

    def list_providers(self) -> list[str]:
        """List registered provider names."""
        return list(self._providers.keys())

    def resolve_model_string(self, model_string: str) -> tuple[LLMProvider, str]:
        """Resolve a model string to provider and model.

        Args:
            model_string: Model string like "anthropic/opus" or just "opus"

        Returns:
            Tuple of (provider, resolved_model)
        """
        if "/" in model_string:
            provider_name, model = model_string.split("/", 1)
        else:
            provider_name = self.DEFAULT_PROVIDER
            model = model_string

        provider = self.get(provider_name)
        resolved_model = provider.resolve_alias(model)
        return provider, resolved_model

    def validate_model_string(self, model_string: str) -> bool:
        """Validate a model string.

        Args:
            model_string: Model string to validate

        Returns:
            True if valid
        """
        try:
            provider, model = self.resolve_model_string(model_string)
            return provider.validate_model(model)
        except KeyError:
            return False
