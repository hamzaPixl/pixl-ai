"""Tests for providers — AnthropicProvider, ProviderRegistry, and LLMProvider base.

Tests cover:
- AnthropicProvider.validate_model() — valid/invalid/aliased models
- AnthropicProvider.resolve_alias() — known and unknown aliases
- AnthropicProvider.capabilities — property values
- AnthropicProvider.name — property
- ProviderRegistry.get() — success and KeyError
- ProviderRegistry.list_providers() — registered names
- ProviderRegistry.resolve_model_string() — slash-delimited and undelimited
- ProviderRegistry.validate_model_string() — valid/invalid/unknown provider
- LLMProvider.resolve_alias() default — identity
- LLMProvider.parse_model_string() — with/without slash
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from pixl.providers.anthropic_provider import AnthropicProvider
from pixl.providers.base import LLMProvider, ProviderCapabilities
from pixl.providers.registry import ProviderRegistry

# ---------------------------------------------------------------------------
# AnthropicProvider — resolve_alias
# ---------------------------------------------------------------------------


class TestAnthropicProviderResolveAlias:
    def setup_method(self) -> None:
        self.provider = AnthropicProvider()

    def test_resolves_opus_alias(self) -> None:
        assert self.provider.resolve_alias("opus") == "claude-opus-4-6"

    def test_resolves_sonnet_alias(self) -> None:
        assert self.provider.resolve_alias("sonnet") == "claude-sonnet-4-6"

    def test_resolves_haiku_alias(self) -> None:
        assert self.provider.resolve_alias("haiku") == "claude-haiku-4-5"

    def test_resolves_glm_alias(self) -> None:
        assert self.provider.resolve_alias("glm") == "glm-5"

    def test_unknown_alias_returns_unchanged(self) -> None:
        assert self.provider.resolve_alias("claude-sonnet-4-6") == "claude-sonnet-4-6"

    def test_empty_string_returns_empty(self) -> None:
        assert self.provider.resolve_alias("") == ""

    def test_random_string_returned_unchanged(self) -> None:
        result = self.provider.resolve_alias("totally-unknown-model-xyz")
        assert result == "totally-unknown-model-xyz"


# ---------------------------------------------------------------------------
# AnthropicProvider — validate_model
# ---------------------------------------------------------------------------


class TestAnthropicProviderValidateModel:
    def setup_method(self) -> None:
        self.provider = AnthropicProvider()

    def test_valid_exact_model_name_returns_true(self) -> None:
        assert self.provider.validate_model("claude-sonnet-4-6") is True

    def test_valid_opus_model_returns_true(self) -> None:
        assert self.provider.validate_model("claude-opus-4-6") is True

    def test_valid_haiku_model_returns_true(self) -> None:
        assert self.provider.validate_model("claude-haiku-4-5") is True

    def test_valid_alias_resolves_and_returns_true(self) -> None:
        assert self.provider.validate_model("sonnet") is True

    def test_haiku_alias_resolves_and_returns_true(self) -> None:
        assert self.provider.validate_model("haiku") is True

    def test_invalid_model_returns_false(self) -> None:
        assert self.provider.validate_model("gpt-99-mega") is False

    def test_empty_string_returns_false(self) -> None:
        assert self.provider.validate_model("") is False

    def test_model_with_provider_prefix_returns_false(self) -> None:
        # Provider-prefixed strings are not in VALID_MODELS
        assert self.provider.validate_model("anthropic/claude-sonnet-4-6") is False

    def test_glm_model_returns_true(self) -> None:
        assert self.provider.validate_model("glm-5") is True

    def test_glm_alias_resolves_and_returns_true(self) -> None:
        assert self.provider.validate_model("glm") is True


# ---------------------------------------------------------------------------
# AnthropicProvider — properties
# ---------------------------------------------------------------------------


class TestAnthropicProviderProperties:
    def setup_method(self) -> None:
        self.provider = AnthropicProvider()

    def test_name_is_anthropic(self) -> None:
        assert self.provider.name == "anthropic"

    def test_capabilities_supports_streaming(self) -> None:
        assert self.provider.capabilities.supports_streaming is True

    def test_capabilities_supports_vision(self) -> None:
        assert self.provider.capabilities.supports_vision is True

    def test_capabilities_supports_tools(self) -> None:
        assert self.provider.capabilities.supports_tools is True

    def test_capabilities_returns_provider_capabilities_instance(self) -> None:
        assert isinstance(self.provider.capabilities, ProviderCapabilities)

    def test_capabilities_max_context_tokens(self) -> None:
        assert self.provider.capabilities.max_context_tokens == 200000


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def setup_method(self) -> None:
        self.registry = ProviderRegistry()

    def test_get_anthropic_provider(self) -> None:
        provider = self.registry.get("anthropic")
        assert isinstance(provider, AnthropicProvider)

    def test_get_unknown_provider_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown provider"):
            self.registry.get("nonexistent-provider")

    def test_list_providers_includes_anthropic(self) -> None:
        names = self.registry.list_providers()
        assert "anthropic" in names

    def test_list_providers_includes_gemini(self) -> None:
        names = self.registry.list_providers()
        assert "gemini" in names

    def test_list_providers_includes_codex(self) -> None:
        names = self.registry.list_providers()
        assert "codex" in names

    def test_list_providers_returns_list_of_strings(self) -> None:
        names = self.registry.list_providers()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_register_custom_provider(self) -> None:
        class FakeProvider(LLMProvider):
            @property
            def name(self) -> str:
                return "fake"

            @property
            def capabilities(self) -> ProviderCapabilities:
                return ProviderCapabilities()

            async def query(self, prompt, **kwargs) -> AsyncIterator[dict[str, Any]]:
                async def _gen():
                    yield {}
                return _gen()

            def validate_model(self, model: str) -> bool:
                return model == "fake-model"

        fake = FakeProvider()
        self.registry.register(fake)
        assert self.registry.get("fake") is fake

    def test_default_provider_is_anthropic(self) -> None:
        assert ProviderRegistry.DEFAULT_PROVIDER == "anthropic"


# ---------------------------------------------------------------------------
# ProviderRegistry — resolve_model_string
# ---------------------------------------------------------------------------


class TestProviderRegistryResolveModelString:
    def setup_method(self) -> None:
        self.registry = ProviderRegistry()

    def test_slash_format_routes_to_correct_provider(self) -> None:
        provider, model = self.registry.resolve_model_string("anthropic/claude-sonnet-4-6")
        assert provider.name == "anthropic"
        assert model == "claude-sonnet-4-6"

    def test_slash_format_resolves_alias(self) -> None:
        provider, model = self.registry.resolve_model_string("anthropic/sonnet")
        assert model == "claude-sonnet-4-6"

    def test_no_slash_defaults_to_anthropic_provider(self) -> None:
        provider, model = self.registry.resolve_model_string("opus")
        assert provider.name == "anthropic"

    def test_no_slash_resolves_alias_via_default_provider(self) -> None:
        provider, model = self.registry.resolve_model_string("opus")
        assert model == "claude-opus-4-6"

    def test_gemini_provider_resolved_correctly(self) -> None:
        provider, _ = self.registry.resolve_model_string("gemini/gemini-2.5-pro")
        assert provider.name == "gemini"

    def test_unknown_provider_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            self.registry.resolve_model_string("unknown-provider/model-x")


# ---------------------------------------------------------------------------
# ProviderRegistry — validate_model_string
# ---------------------------------------------------------------------------


class TestProviderRegistryValidateModelString:
    def setup_method(self) -> None:
        self.registry = ProviderRegistry()

    def test_valid_full_model_string_returns_true(self) -> None:
        result = self.registry.validate_model_string("anthropic/claude-sonnet-4-6")
        assert result is True

    def test_valid_alias_string_returns_true(self) -> None:
        result = self.registry.validate_model_string("anthropic/sonnet")
        assert result is True

    def test_invalid_model_returns_false(self) -> None:
        result = self.registry.validate_model_string("anthropic/super-fake-model-99")
        assert result is False

    def test_unknown_provider_returns_false(self) -> None:
        result = self.registry.validate_model_string("totally-unknown-provider/model")
        assert result is False


# ---------------------------------------------------------------------------
# LLMProvider base — resolve_alias and parse_model_string
# ---------------------------------------------------------------------------


class TestLLMProviderBase:
    def _make_concrete_provider(self) -> LLMProvider:
        class ConcreteProvider(LLMProvider):
            @property
            def name(self) -> str:
                return "concrete"

            @property
            def capabilities(self) -> ProviderCapabilities:
                return ProviderCapabilities()

            async def query(self, prompt, **kwargs) -> AsyncIterator[dict[str, Any]]:
                async def _gen():
                    yield {}
                return _gen()

            def validate_model(self, model: str) -> bool:
                return model == "valid-model"

        return ConcreteProvider()

    def test_resolve_alias_default_is_identity(self) -> None:
        provider = self._make_concrete_provider()
        assert provider.resolve_alias("any-model") == "any-model"

    def test_parse_model_string_with_slash(self) -> None:
        provider = self._make_concrete_provider()
        p, m = provider.parse_model_string("anthropic/claude-sonnet-4-6")
        assert p == "anthropic"
        assert m == "claude-sonnet-4-6"

    def test_parse_model_string_without_slash(self) -> None:
        provider = self._make_concrete_provider()
        p, m = provider.parse_model_string("claude-sonnet-4-6")
        assert p == "concrete"
        assert m == "claude-sonnet-4-6"

    def test_get_usage_limits_returns_unavailable_by_default(self) -> None:
        import asyncio

        provider = self._make_concrete_provider()
        result = asyncio.run(provider.get_usage_limits())
        assert result.available is False
        assert result.provider == "concrete"

    def test_capabilities_default_values(self) -> None:
        caps = ProviderCapabilities()
        assert caps.supports_streaming is True
        assert caps.supports_tools is True
        assert caps.supports_vision is False
        assert caps.supports_function_calling is True
        assert caps.is_agentic is False
