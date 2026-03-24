"""Unit tests for pixl.config.providers — provider configuration and model resolution.

All tests are pure-Python (no I/O, no external deps) since the module
logic being tested is self-contained pydantic models with no side effects.
The file-loading helpers (load_providers_config) are tested using a tmp_path
fixture so they exercise the real filesystem path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pixl.config.providers import (
    ConcurrencyConfig,
    DEFAULT_MODELS,
    DEFAULT_PROVIDERS,
    ProviderConfig,
    ProvidersConfig,
    load_providers_config,
)


# ---------------------------------------------------------------------------
# ProvidersConfig — parse_model_string
# ---------------------------------------------------------------------------


class TestParseModelString:
    def test_parses_provider_slash_model_format(self) -> None:
        # Arrange
        config = ProvidersConfig()

        # Act
        provider, model = config.parse_model_string("anthropic/claude-sonnet-4-6")

        # Assert
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-6"

    def test_parses_model_without_provider_uses_default(self) -> None:
        config = ProvidersConfig(default_provider="anthropic")
        provider, model = config.parse_model_string("claude-haiku-4-5")
        assert provider == "anthropic"
        assert model == "claude-haiku-4-5"

    def test_parses_gemini_provider(self) -> None:
        config = ProvidersConfig()
        provider, model = config.parse_model_string("gemini/gemini-2.5-pro")
        assert provider == "gemini"
        assert model == "gemini-2.5-pro"

    def test_parses_codex_with_colon_variant(self) -> None:
        """Model names may contain colons — only split on the first slash."""
        config = ProvidersConfig()
        provider, model = config.parse_model_string("codex/gpt-5.2-codex:xhigh")
        assert provider == "codex"
        assert model == "gpt-5.2-codex:xhigh"

    def test_parses_model_with_multiple_slashes_only_splits_first(self) -> None:
        config = ProvidersConfig()
        provider, model = config.parse_model_string("anthropic/a/b")
        assert provider == "anthropic"
        assert model == "a/b"


# ---------------------------------------------------------------------------
# ProvidersConfig — is_allowed_model
# ---------------------------------------------------------------------------


class TestIsAllowedModel:
    def test_returns_true_for_model_in_allowlist(self) -> None:
        config = ProvidersConfig()
        assert config.is_allowed_model("anthropic/claude-sonnet-4-6") is True

    def test_returns_false_for_model_not_in_allowlist(self) -> None:
        config = ProvidersConfig()
        assert config.is_allowed_model("anthropic/gpt-fake-99") is False

    def test_empty_models_list_rejects_everything(self) -> None:
        config = ProvidersConfig(models=[])
        assert config.is_allowed_model("anthropic/claude-sonnet-4-6") is False

    def test_custom_models_list_is_respected(self) -> None:
        config = ProvidersConfig(models=["openai/gpt-4o"])
        assert config.is_allowed_model("openai/gpt-4o") is True
        assert config.is_allowed_model("anthropic/claude-sonnet-4-6") is False


# ---------------------------------------------------------------------------
# ProvidersConfig — get_provider_config
# ---------------------------------------------------------------------------


class TestGetProviderConfig:
    def test_returns_config_for_known_provider(self) -> None:
        config = ProvidersConfig()
        result = config.get_provider_config("anthropic")
        assert result is not None
        assert result.name == "anthropic"

    def test_returns_none_for_unknown_provider(self) -> None:
        config = ProvidersConfig()
        result = config.get_provider_config("unknown-llm-service")
        assert result is None

    def test_returns_config_for_codex(self) -> None:
        config = ProvidersConfig()
        result = config.get_provider_config("codex")
        assert result is not None
        assert result.api_key_env == "CODEX_API_KEY"

    def test_returns_config_for_gemini(self) -> None:
        config = ProvidersConfig()
        result = config.get_provider_config("gemini")
        assert result is not None
        assert result.api_key_env == "GEMINI_API_KEY"


# ---------------------------------------------------------------------------
# ProviderConfig validation
# ---------------------------------------------------------------------------


class TestProviderConfig:
    def test_enabled_defaults_to_true(self) -> None:
        provider = ProviderConfig(name="test-llm", api_key_env="TEST_KEY")
        assert provider.enabled is True

    def test_base_url_defaults_to_none(self) -> None:
        provider = ProviderConfig(name="test-llm", api_key_env="TEST_KEY")
        assert provider.base_url is None

    def test_custom_base_url_is_preserved(self) -> None:
        provider = ProviderConfig(
            name="custom", api_key_env="CUSTOM_KEY", base_url="https://api.custom.com"
        )
        assert provider.base_url == "https://api.custom.com"


# ---------------------------------------------------------------------------
# ConcurrencyConfig validation
# ---------------------------------------------------------------------------


class TestConcurrencyConfig:
    def test_default_concurrency_is_three(self) -> None:
        config = ConcurrencyConfig()
        assert config.default_concurrency == 3

    def test_rejects_concurrency_below_one(self) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError
            ConcurrencyConfig(default_concurrency=0)

    def test_provider_concurrency_defaults_to_empty_dict(self) -> None:
        config = ConcurrencyConfig()
        assert config.provider_concurrency == {}

    def test_model_concurrency_defaults_to_empty_dict(self) -> None:
        config = ConcurrencyConfig()
        assert config.model_concurrency == {}


# ---------------------------------------------------------------------------
# DEFAULT_MODELS list integrity
# ---------------------------------------------------------------------------


class TestDefaultModels:
    def test_all_default_models_have_provider_prefix(self) -> None:
        for model in DEFAULT_MODELS:
            assert "/" in model, f"Model {model!r} lacks provider prefix"

    def test_no_empty_model_strings(self) -> None:
        assert all(m.strip() for m in DEFAULT_MODELS)

    def test_default_model_is_in_allowlist(self) -> None:
        config = ProvidersConfig()
        assert config.is_allowed_model(config.default_model) is True


# ---------------------------------------------------------------------------
# DEFAULT_PROVIDERS integrity
# ---------------------------------------------------------------------------


class TestDefaultProviders:
    def test_anthropic_is_in_default_providers(self) -> None:
        assert "anthropic" in DEFAULT_PROVIDERS

    def test_codex_is_in_default_providers(self) -> None:
        assert "codex" in DEFAULT_PROVIDERS

    def test_gemini_is_in_default_providers(self) -> None:
        assert "gemini" in DEFAULT_PROVIDERS

    def test_all_default_providers_have_name_set(self) -> None:
        for key, provider in DEFAULT_PROVIDERS.items():
            assert provider.name == key, (
                f"Provider {key!r} has mismatched name {provider.name!r}"
            )


# ---------------------------------------------------------------------------
# load_providers_config — file-based loading
# ---------------------------------------------------------------------------


class TestLoadProvidersConfig:
    def test_returns_defaults_when_no_config_file(self, tmp_path: Path) -> None:
        # tmp_path has no .pixl directory
        config = load_providers_config(tmp_path)
        assert isinstance(config, ProvidersConfig)
        assert config.default_provider == "anthropic"

    def test_overrides_default_provider_from_file(self, tmp_path: Path) -> None:
        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir()
        (pixl_dir / "providers.yaml").write_text(
            yaml.dump({"default_provider": "gemini"})
        )
        config = load_providers_config(tmp_path)
        assert config.default_provider == "gemini"

    def test_overrides_models_allowlist_from_file(self, tmp_path: Path) -> None:
        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir()
        custom_models = ["openai/gpt-4o", "anthropic/claude-sonnet-4-6"]
        (pixl_dir / "providers.yaml").write_text(
            yaml.dump({"models": custom_models})
        )
        config = load_providers_config(tmp_path)
        assert config.models == custom_models

    def test_adds_custom_provider_from_file(self, tmp_path: Path) -> None:
        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir()
        yaml_content = yaml.dump({
            "providers": {
                "my-provider": {
                    "api_key_env": "MY_PROVIDER_KEY",
                    "enabled": True,
                }
            }
        })
        (pixl_dir / "providers.yaml").write_text(yaml_content)
        config = load_providers_config(tmp_path)
        assert "my-provider" in config.providers
        assert config.providers["my-provider"].api_key_env == "MY_PROVIDER_KEY"

    def test_overrides_concurrency_from_file(self, tmp_path: Path) -> None:
        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir()
        (pixl_dir / "providers.yaml").write_text(
            yaml.dump({"concurrency": {"default_concurrency": 7}})
        )
        config = load_providers_config(tmp_path)
        assert config.concurrency.default_concurrency == 7

    def test_empty_yaml_file_uses_defaults(self, tmp_path: Path) -> None:
        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir()
        (pixl_dir / "providers.yaml").write_text("")
        config = load_providers_config(tmp_path)
        # Should fall back to defaults cleanly
        assert config.default_provider == "anthropic"


# ---------------------------------------------------------------------------
# ProvidersConfig — execution mode defaults
# ---------------------------------------------------------------------------


class TestExecutionModeConfig:
    def test_default_mode_is_interactive(self) -> None:
        config = ProvidersConfig()
        assert config.execution.mode == "interactive"

    def test_require_approval_for_destructive_defaults_true(self) -> None:
        config = ProvidersConfig()
        assert config.execution.require_approval_for_destructive is True

    def test_auto_approve_gates_defaults_empty(self) -> None:
        config = ProvidersConfig()
        assert config.execution.auto_approve_gates == []


# ---------------------------------------------------------------------------
# ProvidersConfig — git strategy defaults
# ---------------------------------------------------------------------------


class TestGitStrategyConfig:
    def test_default_strategy_is_per_feature(self) -> None:
        config = ProvidersConfig()
        assert config.git.strategy == "per_feature"

    def test_atomic_commits_defaults_false(self) -> None:
        config = ProvidersConfig()
        assert config.git.atomic_commits is False

    def test_commit_format_defaults_to_conventional(self) -> None:
        config = ProvidersConfig()
        assert config.git.commit_format == "conventional"
