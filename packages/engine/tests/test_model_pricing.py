"""Tests for externalized model pricing (T-30).

Tests cover:
- load_model_pricing() loads from pricing.yaml
- load_model_pricing() falls back to hardcoded defaults when file is missing
- _estimate_cost() uses config-loaded pricing
- _estimate_cost() logs a WARNING when model is not found
- _estimate_cost() returns $0 for unknown models
- Pricing cache reset works correctly
"""

from __future__ import annotations

import logging
from unittest.mock import mock_open, patch

import pytest
import yaml
from pixl.config.providers import (
    _FALLBACK_MODEL_PRICING,
    _reset_pricing_cache,
    load_model_pricing,
)


@pytest.fixture(autouse=True)
def _clear_pricing_cache():
    """Reset pricing cache before and after each test."""
    _reset_pricing_cache()
    yield
    _reset_pricing_cache()


# ---------------------------------------------------------------------------
# load_model_pricing
# ---------------------------------------------------------------------------


class TestLoadModelPricing:
    def test_should_load_pricing_from_yaml(self) -> None:
        pricing = load_model_pricing()
        # Must have entries (loaded from the real bundled pricing.yaml)
        assert len(pricing) > 0

    def test_should_include_anthropic_models(self) -> None:
        pricing = load_model_pricing()
        assert "claude-sonnet-4-6" in pricing
        assert "claude-opus-4-6" in pricing
        assert "claude-haiku-4-5" in pricing

    def test_should_include_gemini_models(self) -> None:
        pricing = load_model_pricing()
        assert "gemini-2.5-pro" in pricing
        assert "gemini-2.5-flash" in pricing

    def test_should_include_codex_models(self) -> None:
        pricing = load_model_pricing()
        assert "gpt-5.2-codex" in pricing

    def test_pricing_values_are_tuples_of_floats(self) -> None:
        pricing = load_model_pricing()
        for model, rates in pricing.items():
            assert isinstance(rates, tuple), f"{model}: expected tuple, got {type(rates)}"
            assert len(rates) == 2, f"{model}: expected 2 elements, got {len(rates)}"
            assert isinstance(rates[0], float), f"{model}: input rate not float"
            assert isinstance(rates[1], float), f"{model}: output rate not float"

    def test_should_cache_pricing_on_subsequent_calls(self) -> None:
        first = load_model_pricing()
        second = load_model_pricing()
        assert first is second  # Same object reference (cached)

    def test_should_fallback_to_defaults_when_file_missing(self) -> None:
        with patch("builtins.open", side_effect=FileNotFoundError("no such file")):
            pricing = load_model_pricing()

        assert pricing == _FALLBACK_MODEL_PRICING

    def test_should_fallback_when_yaml_has_unexpected_format(self) -> None:
        bad_yaml = "just_a_string"
        with patch("builtins.open", mock_open(read_data=bad_yaml)):
            pricing = load_model_pricing()

        assert pricing == _FALLBACK_MODEL_PRICING

    def test_should_fallback_when_yaml_has_no_models_key(self) -> None:
        no_models = yaml.dump({"something_else": {}})
        with patch("builtins.open", mock_open(read_data=no_models)):
            pricing = load_model_pricing()

        assert pricing == _FALLBACK_MODEL_PRICING

    def test_should_skip_malformed_entries_and_load_valid_ones(self) -> None:
        mixed_yaml = yaml.dump({
            "models": {
                "good-model": {"input": 1.0, "output": 2.0},
                "bad-model": {"only_input": 1.0},
            }
        })
        with patch("builtins.open", mock_open(read_data=mixed_yaml)):
            pricing = load_model_pricing()

        assert "good-model" in pricing
        assert "bad-model" not in pricing

    def test_should_fallback_when_all_entries_malformed(self) -> None:
        all_bad = yaml.dump({
            "models": {
                "bad-1": "not_a_dict",
                "bad-2": {"only_input": 1.0},
            }
        })
        with patch("builtins.open", mock_open(read_data=all_bad)):
            pricing = load_model_pricing()

        assert pricing == _FALLBACK_MODEL_PRICING


# ---------------------------------------------------------------------------
# _estimate_cost (via task_executor)
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def _estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Import and call _estimate_cost from task_executor."""
        from pixl.execution.task_executor import _estimate_cost

        return _estimate_cost(input_tokens, output_tokens, model)

    def test_should_calculate_cost_for_known_model(self) -> None:
        # claude-sonnet-4-6: input=3.0, output=15.0 per 1M tokens
        cost = self._estimate_cost(1_000_000, 100_000, "claude-sonnet-4-6")
        expected = (1_000_000 * 3.0 + 100_000 * 15.0) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_should_calculate_cost_for_opus(self) -> None:
        cost = self._estimate_cost(500_000, 50_000, "claude-opus-4-6")
        expected = (500_000 * 15.0 + 50_000 * 75.0) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_should_calculate_cost_for_haiku(self) -> None:
        cost = self._estimate_cost(2_000_000, 200_000, "claude-haiku-4-5")
        expected = (2_000_000 * 0.80 + 200_000 * 4.0) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_should_match_model_by_substring(self) -> None:
        # Model string with prefix should still match
        cost = self._estimate_cost(1_000_000, 0, "anthropic/claude-sonnet-4-6")
        assert cost > 0

    def test_should_return_zero_for_unknown_model(self) -> None:
        cost = self._estimate_cost(1_000_000, 1_000_000, "totally-unknown-model-xyz")
        assert cost == 0.0

    def test_should_log_warning_for_unknown_model(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING, logger="pixl.execution.task_executor"):
            self._estimate_cost(1_000, 1_000, "unknown-model-abc")

        assert any("No pricing data for model" in record.message for record in caplog.records), (
            f"Expected warning about missing pricing, got: {[r.message for r in caplog.records]}"
        )

    def test_should_not_log_warning_for_known_model(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="pixl.execution.task_executor"):
            self._estimate_cost(1_000, 1_000, "claude-sonnet-4-6")

        pricing_warnings = [
            r for r in caplog.records if "No pricing data" in r.message
        ]
        assert len(pricing_warnings) == 0

    def test_should_return_zero_cost_for_zero_tokens(self) -> None:
        cost = self._estimate_cost(0, 0, "claude-sonnet-4-6")
        assert cost == 0.0
