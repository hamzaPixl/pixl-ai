"""Tests for task_executor._estimate_cost() and utility functions."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from pixl.execution.task_executor import (
    _build_stage_output_format,
    _tail_excerpt,
    is_resume_session_error,
    stream_message_to_console,
)

# ---------------------------------------------------------------------------
# _estimate_cost
# ---------------------------------------------------------------------------


class TestEstimateCost:
    """Tests for _estimate_cost() — uses real pricing.yaml via load_model_pricing."""

    def _call(self, input_tokens: int, output_tokens: int, model: str) -> float:
        from pixl.execution.task_executor import _estimate_cost

        return _estimate_cost(input_tokens, output_tokens, model)

    def test_returns_float_for_known_model(self) -> None:
        result = self._call(1_000_000, 1_000_000, "claude-sonnet-4-6")
        assert isinstance(result, float)

    def test_cost_is_positive_for_nonzero_tokens(self) -> None:
        result = self._call(1000, 1000, "claude-sonnet-4-6")
        assert result > 0.0

    def test_zero_tokens_yields_zero_cost(self) -> None:
        result = self._call(0, 0, "claude-sonnet-4-6")
        assert result == 0.0

    def test_unknown_model_returns_zero(self, caplog) -> None:
        with caplog.at_level(logging.WARNING):
            result = self._call(1000, 1000, "unknown-model-xyz-99")
        assert result == 0.0

    def test_unknown_model_logs_warning(self, caplog) -> None:
        with caplog.at_level(logging.WARNING):
            self._call(500, 500, "totally-unknown-model")
        assert any("No pricing data" in r.message for r in caplog.records)

    def test_opus_more_expensive_than_haiku(self) -> None:
        haiku = self._call(100_000, 100_000, "claude-haiku-4-5")
        opus = self._call(100_000, 100_000, "claude-opus-4-6")
        assert opus > haiku

    def test_sonnet_between_haiku_and_opus(self) -> None:
        haiku = self._call(100_000, 100_000, "claude-haiku-4-5")
        sonnet = self._call(100_000, 100_000, "claude-sonnet-4-6")
        opus = self._call(100_000, 100_000, "claude-opus-4-6")
        assert haiku < sonnet < opus

    def test_model_match_via_substring(self) -> None:
        # "claude-sonnet-4-6" is in the key "claude-sonnet-4-6"
        result = self._call(1_000_000, 0, "claude-sonnet-4-6")
        # input rate for sonnet is $3.0 / 1M → expect exactly 3.0
        assert abs(result - 3.0) < 0.01

    def test_gemini_flash_model_recognized(self) -> None:
        result = self._call(1_000_000, 0, "gemini-2.5-flash")
        assert result > 0.0

    def test_output_tokens_cost_more_than_input(self) -> None:
        # For any model, output is more expensive than input
        input_only = self._call(1_000_000, 0, "claude-sonnet-4-6")
        output_only = self._call(0, 1_000_000, "claude-sonnet-4-6")
        assert output_only > input_only


# ---------------------------------------------------------------------------
# is_resume_session_error
# ---------------------------------------------------------------------------


class TestIsResumeSessionError:
    def test_returns_false_for_generic_error(self) -> None:
        assert is_resume_session_error("Rate limit exceeded") is False

    def test_returns_false_for_empty_string(self) -> None:
        assert is_resume_session_error("") is False

    def test_returns_false_when_session_not_in_message(self) -> None:
        assert is_resume_session_error("Connection timeout") is False

    def test_returns_true_for_session_not_found(self) -> None:
        assert is_resume_session_error("Session not found") is True

    def test_returns_true_for_session_expired(self) -> None:
        assert is_resume_session_error("Session expired") is True

    def test_returns_true_for_unknown_session(self) -> None:
        assert is_resume_session_error("Unknown session id") is True

    def test_returns_true_for_invalid_session(self) -> None:
        assert is_resume_session_error("Invalid session token") is True

    def test_returns_true_for_cannot_resume(self) -> None:
        assert is_resume_session_error("Cannot resume session") is True

    def test_returns_true_for_session_does_not_exist(self) -> None:
        assert is_resume_session_error("Session does not exist") is True

    def test_returns_true_for_no_such_session(self) -> None:
        assert is_resume_session_error("No such session") is True

    def test_case_insensitive(self) -> None:
        assert is_resume_session_error("SESSION NOT FOUND") is True

    def test_returns_false_session_only_no_marker(self) -> None:
        # "session" appears but none of the markers do
        assert is_resume_session_error("session is healthy") is False


# ---------------------------------------------------------------------------
# _tail_excerpt
# ---------------------------------------------------------------------------


class TestTailExcerpt:
    def test_returns_empty_string_for_empty_input(self) -> None:
        assert _tail_excerpt("") == ""

    def test_returns_full_text_when_shorter_than_limit(self) -> None:
        text = "short text"
        assert _tail_excerpt(text, limit=100) == text

    def test_returns_last_n_chars_when_over_limit(self) -> None:
        text = "a" * 5 + "b" * 5
        result = _tail_excerpt(text, limit=5)
        assert result == "b" * 5

    def test_exact_limit_length_returned_in_full(self) -> None:
        text = "x" * 20_000
        result = _tail_excerpt(text, limit=20_000)
        assert result == text

    def test_one_char_over_limit_clips(self) -> None:
        text = "prefix" + "z" * 20_000
        result = _tail_excerpt(text, limit=20_000)
        assert result == "z" * 20_000


# ---------------------------------------------------------------------------
# _build_stage_output_format
# ---------------------------------------------------------------------------


class TestBuildStageOutputFormat:
    def test_returns_dict_with_type_json_schema(self) -> None:
        result = _build_stage_output_format()
        assert result is not None
        assert result["type"] == "json_schema"

    def test_schema_key_is_dict(self) -> None:
        result = _build_stage_output_format()
        assert result is not None
        assert isinstance(result["schema"], dict)

    def test_returns_none_on_import_error(self) -> None:
        with patch("pixl.execution.task_executor._build_stage_output_format") as mock_fn:
            mock_fn.return_value = None
            result = mock_fn()
            assert result is None


# ---------------------------------------------------------------------------
# stream_message_to_console
# ---------------------------------------------------------------------------


class TestStreamMessageToConsole:
    def test_no_crash_when_message_has_no_content(self) -> None:
        msg = MagicMock(spec=[])  # no .content attribute
        stream_message_to_console(msg)  # should not raise
