"""Storage for provider usage limits."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pixl.models.usage_limits import ProviderUsageLimits
from pixl.paths import get_pixl_dir


class UsageLimitsStore:
    """Manages persistence of provider usage limits.

    Stores limits per-provider in .pixl/usage_limits.json.
    Supports caching with TTL to avoid excessive API calls.
    """

    # Cache TTL in seconds (5 minutes default)
    DEFAULT_CACHE_TTL = 300

    def __init__(self, project_path: Path, cache_ttl: int = DEFAULT_CACHE_TTL) -> None:
        self.project_path = project_path
        self.pixl_dir = get_pixl_dir(project_path)
        self.limits_path = self.pixl_dir / "usage_limits.json"
        self.cache_ttl = cache_ttl

    def _ensure_dir(self) -> None:
        """Ensure .pixl directory exists."""
        self.pixl_dir.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> dict[str, dict[str, Any]]:
        """Load all limits from disk."""
        if not self.limits_path.exists():
            return {}

        with open(self.limits_path, encoding="utf-8") as f:
            result: dict[str, dict[str, Any]] = json.load(f)
            return result

    def _save_all(self, data: dict[str, dict[str, Any]]) -> None:
        """Save all limits to disk."""
        self._ensure_dir()

        with open(self.limits_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def save(self, limits: ProviderUsageLimits) -> None:
        """Save usage limits for a provider.

        Args:
            limits: The usage limits to save
        """
        data = self._load_all()
        data[limits.provider] = limits.model_dump(mode="json")
        self._save_all(data)

    def load(self, provider: str) -> ProviderUsageLimits | None:
        """Load usage limits for a provider.

        Args:
            provider: Provider identifier

        Returns:
            ProviderUsageLimits or None if not found
        """
        data = self._load_all()
        if provider not in data:
            return None

        return ProviderUsageLimits.model_validate(data[provider])

    def get_all(self) -> dict[str, ProviderUsageLimits]:
        """Load all stored usage limits.

        Returns:
            Dict mapping provider name to limits
        """
        data = self._load_all()
        return {
            provider: ProviderUsageLimits.model_validate(limits_data)
            for provider, limits_data in data.items()
        }

    def is_cache_valid(self, provider: str) -> bool:
        """Check if cached limits are still valid (within TTL).

        Args:
            provider: Provider identifier

        Returns:
            True if cache is valid, False otherwise
        """
        limits = self.load(provider)
        if limits is None:
            return False

        age = (datetime.now() - limits.captured_at).total_seconds()
        return age < self.cache_ttl

    def get_cached_or_none(self, provider: str) -> ProviderUsageLimits | None:
        """Get cached limits if valid, otherwise None.

        Args:
            provider: Provider identifier

        Returns:
            Cached limits if valid, None otherwise
        """
        if self.is_cache_valid(provider):
            return self.load(provider)
        return None

    def delete(self, provider: str) -> bool:
        """Delete stored limits for a provider.

        Args:
            provider: Provider identifier

        Returns:
            True if deleted, False if not found
        """
        data = self._load_all()
        if provider not in data:
            return False

        del data[provider]
        self._save_all(data)
        return True

    def clear(self) -> None:
        """Clear all stored limits."""
        if self.limits_path.exists():
            self.limits_path.unlink()

    def exists(self) -> bool:
        """Check if limits file exists."""
        return self.limits_path.exists()
