"""Provider configuration for multi-model support.

This module defines the configuration schema for:
- Providers (Anthropic, Codex, Gemini)
- Concurrency limits per provider/model
- Models allowlist (only these models can be used)

Config search order:
1. project_path/.pixl/providers.yaml               # Local override
2. ~/.pixl/projects/[PROJECT_NAME]/providers.yaml  # Global project-specific
3. ~/.pixl/providers.yaml                          # Global default
4. Bundled defaults                                # Fallback
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from pixl.config.resolver import ConfigSource, find_config_file

# Models Allowlist — ONLY these models can be used

DEFAULT_MODELS: list[str] = [
    "anthropic/claude-opus-4-6",
    "anthropic/claude-opus-4-6",
    "anthropic/claude-sonnet-4-6",
    "anthropic/claude-haiku-4-5",
    "codex/default",
    "codex/codex-5.2",
    "codex/gpt-5.2-codex",
    "codex/gpt-5.2-codex:xhigh",
    "codex/gpt-5.3-codex",
    "codex/gpt-5.3-codex:spark",
    "codex/spark",
    "gemini/gemini-3-pro-preview",
    "gemini/gemini-3-flash-preview",
    "gemini/gemini-2.5-pro",
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.5-flash-lite",
]


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    name: str = Field(..., description="Provider identifier (anthropic, codex, gemini)")
    api_key_env: str = Field(..., description="Environment variable for API key")
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    base_url: str | None = Field(default=None, description="Custom base URL for API")


class ConcurrencyConfig(BaseModel):
    """Concurrency limits to prevent rate limiting."""

    default_concurrency: int = Field(default=3, ge=1)
    provider_concurrency: dict[str, int] = Field(
        default_factory=dict,
        description="Per-provider concurrency limits",
    )
    model_concurrency: dict[str, int] = Field(
        default_factory=dict,
        description="Per-model concurrency limits (provider/model)",
    )


# Default providers
DEFAULT_PROVIDERS: dict[str, ProviderConfig] = {
    "anthropic": ProviderConfig(
        name="anthropic",
        api_key_env="",
    ),
    "codex": ProviderConfig(
        name="codex",
        api_key_env="CODEX_API_KEY",
    ),
    "gemini": ProviderConfig(
        name="gemini",
        api_key_env="GEMINI_API_KEY",
    ),
}


class ExecutionModeConfig(BaseModel):
    """Execution mode configuration controlling human-in-the-loop behavior.

    Modes:
    - interactive: All gates pause for user approval (default)
    - autonomous: Skip all gates automatically
    - custom: Granular per-gate-type control
    """

    mode: str = Field(
        default="interactive",
        description="Execution mode: interactive, autonomous, or custom",
    )
    auto_approve_gates: list[str] = Field(
        default_factory=list,
        description="Gate types to auto-approve in custom mode",
    )
    require_approval_for_destructive: bool = Field(
        default=True,
        description="Always require approval for destructive operations regardless of mode",
    )


class GitStrategyConfig(BaseModel):
    """Git branching strategy configuration.

    Strategies:
    - none: Commit to current branch
    - per_feature: Create a branch per feature (default pixl behavior)
    - per_epic: Create a branch per epic
    - per_milestone: Create a branch per milestone
    """

    strategy: str = Field(
        default="per_feature",
        description="Git branching strategy: none, per_feature, per_epic, per_milestone",
    )
    atomic_commits: bool = Field(
        default=False,
        description="Create commits per task (not per feature). More granular git history.",
    )
    commit_format: str = Field(
        default="conventional",
        description="Commit message format: conventional, simple",
    )
    separate_planning_commits: bool = Field(
        default=False,
        description="Commit planning artifacts separately from implementation",
    )


class ProvidersConfig(BaseModel):
    """Root configuration for providers and model resolution.

    This is the main configuration object that gets loaded from
    .pixl/providers.yaml and provides model resolution.
    """

    models: list[str] = Field(default_factory=lambda: list(DEFAULT_MODELS))
    providers: dict[str, ProviderConfig] = Field(default_factory=lambda: DEFAULT_PROVIDERS.copy())
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    default_provider: str = Field(default="anthropic")
    default_model: str = Field(default="anthropic/claude-sonnet-4-6")

    # Execution mode (GAP-08)
    execution: ExecutionModeConfig = Field(
        default_factory=ExecutionModeConfig,
        description="Execution mode controlling human-in-the-loop behavior",
    )

    # Git strategy (GAP-14)
    git: GitStrategyConfig = Field(
        default_factory=GitStrategyConfig,
        description="Git branching and commit strategy",
    )

    def is_allowed_model(self, model_string: str) -> bool:
        """Check if model is in the allowlist.

        Args:
            model_string: Full model string (e.g., "anthropic/claude-sonnet-4-6")

        Returns:
            True if the model is in the allowlist
        """
        return model_string in self.models

    def parse_model_string(self, model_string: str) -> tuple[str, str]:
        """Parse a model string into provider and model name.

        Args:
            model_string: Either "provider/model" or just "model"

        Returns:
            Tuple of (provider_name, model_name)
        """
        if "/" in model_string:
            parts = model_string.split("/", 1)
            return parts[0], parts[1]
        # No provider specified, use default
        return self.default_provider, model_string

    def get_provider_config(self, provider: str) -> ProviderConfig | None:
        """Get provider configuration.

        Args:
            provider: Provider name

        Returns:
            ProviderConfig or None if not found
        """
        return self.providers.get(provider)


@dataclass
class ProvidersConfigLoadResult:
    """Result of loading providers config including source info."""

    config: ProvidersConfig
    source: ConfigSource

    def __iter__(self) -> Iterator[ProvidersConfig | ConfigSource]:
        """Allow unpacking as tuple."""
        return iter((self.config, self.source))


def load_providers_config(project_path: Path) -> ProvidersConfig:
    """Load providers config from project or use defaults.

    Search order:
    1. project_path/.pixl/providers.yaml               # Local override
    2. ~/.pixl/projects/[PROJECT_NAME]/providers.yaml  # Global project-specific
    3. ~/.pixl/providers.yaml                          # Global default
    4. Bundled defaults                                # Fallback

    Args:
        project_path: Project root directory

    Returns:
        ProvidersConfig with user overrides merged with defaults
    """
    result = load_providers_config_with_source(project_path)
    return result.config


def load_providers_config_with_source(
    project_path: Path,
) -> ProvidersConfigLoadResult:
    """Load providers config with source information.

    Searches for providers.yaml using the standard config resolver.

    Args:
        project_path: Project root directory

    Returns:
        ProvidersConfigLoadResult with config and source info
    """
    config_file, source = find_config_file(project_path, "providers.yaml")

    config = ProvidersConfig()

    if config_file and config_file.exists():
        with open(config_file) as f:
            user_config = yaml.safe_load(f) or {}

        # Override default_provider if specified
        if "default_provider" in user_config:
            config.default_provider = user_config["default_provider"]

        # Override default_model if specified
        if "default_model" in user_config:
            config.default_model = user_config["default_model"]

        # Override models allowlist (replaces defaults entirely)
        if "models" in user_config:
            config.models = user_config["models"]

        if "providers" in user_config:
            for name, prov_data in user_config["providers"].items():
                # Inject name from dict key since it's not in the YAML value
                prov_data_with_name = {**prov_data, "name": name}
                config.providers[name] = ProviderConfig(**prov_data_with_name)

        # Override concurrency if specified
        if "concurrency" in user_config:
            config.concurrency = ConcurrencyConfig(**user_config["concurrency"])

    return ProvidersConfigLoadResult(config=config, source=source)
