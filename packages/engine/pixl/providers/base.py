"""Base class for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from pixl.models.usage_limits import ProviderUsageLimits


class ProviderCapabilities(BaseModel):
    """Capabilities of an LLM provider."""

    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_function_calling: bool = True
    max_context_tokens: int = 128000
    max_output_tokens: int = 8192
    is_agentic: bool = False  # Provider has its own agent loop (tool use, file edits, etc.)


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All providers must implement:
    - name: Provider identifier
    - capabilities: What the provider supports
    - query: Send a query and stream responses
    - validate_model: Check if a model is valid for this provider
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'anthropic', 'openai')."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Provider capabilities."""
        ...

    @abstractmethod
    async def query(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a query and stream responses.

        Args:
            prompt: User prompt
            model: Model to use (provider-specific)
            system_prompt: System prompt
            tools: Tool definitions
            **kwargs: Provider-specific options

        Yields:
            Response chunks as dicts
        """
        ...

    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """Check if a model is valid for this provider.

        Args:
            model: Model identifier

        Returns:
            True if the model is valid
        """
        ...

    def resolve_alias(self, model: str) -> str:
        """Resolve a model alias to full model name.

        Default implementation returns the model unchanged.
        Override in subclasses to add alias support.

        Args:
            model: Model name or alias

        Returns:
            Resolved model name
        """
        return model

    def parse_model_string(self, model_string: str) -> tuple[str, str]:
        """Parse a model string like 'provider/model' into components.

        Args:
            model_string: Full model string

        Returns:
            Tuple of (provider, model)
        """
        if "/" in model_string:
            provider, model = model_string.split("/", 1)
            return provider, model
        return self.name, model_string

    async def get_usage_limits(self) -> "ProviderUsageLimits":
        """Get current rate limits and quotas from the provider API.

        This method makes a minimal API call to retrieve rate limit headers.
        Override in subclasses to implement provider-specific logic.

        Returns:
            ProviderUsageLimits with current limits, or unavailable status
        """
        from pixl.models.usage_limits import ProviderUsageLimits

        # Default implementation returns unavailable
        return ProviderUsageLimits(
            provider=self.name,
            available=False,
            error="Usage limits not implemented for this provider",
        )
