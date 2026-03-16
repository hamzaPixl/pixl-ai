"""Concurrency management for parallel agent execution."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from pixl.config.providers import ConcurrencyConfig

if TYPE_CHECKING:
    from pixl.config.providers import ProvidersConfig


class ConcurrencyManager:
    """Manages concurrency limits for LLM providers.

    Prevents rate limiting by enforcing:
    - Global default concurrency
    - Provider-specific limits (anthropic: 3, openai: 5, etc.)
    - Model-specific limits (opus: 1, etc.)
    """

    def __init__(
        self,
        config: ConcurrencyConfig,
        providers_config: ProvidersConfig | None = None,
    ) -> None:
        self._config = config
        self._providers_config = providers_config
        self._running: dict[str, int] = defaultdict(int)

    @property
    def running_count(self) -> int:
        """Total number of running tasks."""
        return sum(self._running.values())

    def _parse_model_string(self, model_string: str) -> tuple[str, str]:
        if self._providers_config is not None:
            return self._providers_config.parse_model_string(model_string)
        if "/" in model_string:
            provider, model = model_string.split("/", 1)
            return provider, model
        return "anthropic", model_string

    def _get_provider_count(self, provider: str) -> int:
        count = 0
        for key, value in self._running.items():
            if key.startswith(f"{provider}/"):
                count += value
        return count

    def acquire(self, model_string: str) -> bool:
        """Try to acquire a slot for a model."""
        provider, _ = self._parse_model_string(model_string)

        model_limit = self._config.model_concurrency.get(model_string)
        if model_limit is not None and self._running[model_string] >= model_limit:
            return False

        provider_limit = self._config.provider_concurrency.get(
            provider, self._config.default_concurrency
        )
        if self._get_provider_count(provider) >= provider_limit:
            return False

        self._running[model_string] += 1
        return True

    def release(self, model_string: str) -> None:
        """Release a slot for a model."""
        if self._running[model_string] > 0:
            self._running[model_string] -= 1
