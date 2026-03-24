"""Unit tests for OrchestratorCore and module-level helpers in orchestration/core.py."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from pixl.orchestration.core import (
    _BUDGET_BY_TIER,
    _FALLBACK_MAP,
    _UNRECOVERABLE_ERROR_PATTERNS,
    OrchestratorCore,
    _fallback_model_for,
    _is_unrecoverable_api_error,
    _model_budget_usd,
    _model_tier,
)

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_core(tmp_path: Path) -> OrchestratorCore:
    """Instantiate OrchestratorCore with all heavy dependencies mocked out."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch("pixl.orchestration.core.BacklogStore"),
        patch("pixl.orchestration.core.BoulderStore"),
        patch("pixl.orchestration.core.ConfigStore"),
        patch("pixl.orchestration.core.load_providers_config") as mock_lpc,
        patch("pixl.orchestration.core.ProviderRegistry"),
        patch("pixl.orchestration.core.ConcurrencyManager"),
        patch("pixl.orchestration.core.BackgroundManager"),
        patch("pixl.orchestration.core.AgentRegistry"),
        patch("pixl.orchestration.core._resolve_crew_plugin_path", return_value=None),
    ):
        providers_cfg = MagicMock()
        providers_cfg.concurrency = MagicMock()
        mock_lpc.return_value = providers_cfg
        core = OrchestratorCore(project_path=tmp_path)

    return core


# ---------------------------------------------------------------------------
# _is_unrecoverable_api_error
# ---------------------------------------------------------------------------


class TestIsUnrecoverableApiError:
    def test_should_return_false_for_empty_string(self) -> None:
        assert _is_unrecoverable_api_error("") is False

    def test_should_return_false_for_normal_text(self) -> None:
        assert _is_unrecoverable_api_error("Everything is fine.") is False

    def test_should_detect_tool_use_name_length_pattern_1(self) -> None:
        text = "tool_use.name: String should have at most 64 characters"
        assert _is_unrecoverable_api_error(text) is True

    def test_should_detect_tool_use_name_length_pattern_2(self) -> None:
        text = "tool_use.name: string length must be less than 64"
        assert _is_unrecoverable_api_error(text) is True

    def test_should_detect_messages_content_pattern(self) -> None:
        text = "messages.*.content.*.tool_use.name: invalid value"
        assert _is_unrecoverable_api_error(text) is True

    def test_should_return_false_for_partial_match_not_in_patterns(self) -> None:
        # A string that mentions "tool_use" but not the exact pattern
        text = "tool_use.description: String should have at most 100 characters"
        assert _is_unrecoverable_api_error(text) is False

    def test_should_handle_multiline_text_with_pattern(self) -> None:
        text = "Some preamble\ntool_use.name: String should have at most 64 characters\nSome tail"
        assert _is_unrecoverable_api_error(text) is True

    def test_all_defined_patterns_are_detected(self) -> None:
        for pattern in _UNRECOVERABLE_ERROR_PATTERNS:
            assert _is_unrecoverable_api_error(pattern) is True, (
                f"Pattern not detected: {pattern!r}"
            )


# ---------------------------------------------------------------------------
# _model_tier
# ---------------------------------------------------------------------------


class TestModelTier:
    def test_should_detect_opus_tier(self) -> None:
        assert _model_tier("claude-opus-4-6") == "opus"

    def test_should_detect_sonnet_tier(self) -> None:
        assert _model_tier("claude-sonnet-4-6") == "sonnet"

    def test_should_detect_haiku_tier(self) -> None:
        assert _model_tier("claude-haiku-4-5") == "haiku"

    def test_should_return_none_for_unknown_model(self) -> None:
        assert _model_tier("gpt-5-turbo") is None

    def test_should_be_case_insensitive(self) -> None:
        assert _model_tier("CLAUDE-OPUS-3") == "opus"
        assert _model_tier("CLAUDE-SONNET-3") == "sonnet"
        assert _model_tier("CLAUDE-HAIKU-3") == "haiku"

    def test_should_return_none_for_empty_string(self) -> None:
        assert _model_tier("") is None


# ---------------------------------------------------------------------------
# _model_budget_usd
# ---------------------------------------------------------------------------


class TestModelBudgetUsd:
    def test_should_return_haiku_budget(self) -> None:
        assert _model_budget_usd("claude-haiku-4-5") == _BUDGET_BY_TIER["haiku"]

    def test_should_return_sonnet_budget(self) -> None:
        assert _model_budget_usd("claude-sonnet-4-6") == _BUDGET_BY_TIER["sonnet"]

    def test_should_return_opus_budget(self) -> None:
        assert _model_budget_usd("claude-opus-4-6") == _BUDGET_BY_TIER["opus"]

    def test_should_return_none_for_unknown_model(self) -> None:
        assert _model_budget_usd("gpt-5-turbo") is None

    def test_haiku_budget_is_lower_than_sonnet(self) -> None:
        assert _model_budget_usd("claude-haiku-4-5") < _model_budget_usd("claude-sonnet-4-6")  # type: ignore[operator]

    def test_sonnet_budget_is_lower_than_opus(self) -> None:
        assert _model_budget_usd("claude-sonnet-4-6") < _model_budget_usd("claude-opus-4-6")  # type: ignore[operator]


# ---------------------------------------------------------------------------
# _fallback_model_for
# ---------------------------------------------------------------------------


class TestFallbackModelFor:
    def test_should_return_fallback_for_opus(self) -> None:
        result = _fallback_model_for("claude-opus-4-6")
        assert result == _FALLBACK_MAP["opus"]

    def test_should_return_fallback_for_sonnet(self) -> None:
        result = _fallback_model_for("claude-sonnet-4-6")
        assert result == _FALLBACK_MAP["sonnet"]

    def test_should_return_none_for_haiku(self) -> None:
        # haiku has no entry in _FALLBACK_MAP
        assert _fallback_model_for("claude-haiku-4-5") is None

    def test_should_return_none_for_unknown_model(self) -> None:
        assert _fallback_model_for("gpt-5-turbo") is None

    def test_opus_fallback_is_a_string(self) -> None:
        result = _fallback_model_for("claude-opus-4-6")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# OrchestratorCore.__init__
# ---------------------------------------------------------------------------


class TestOrchestratorCoreInit:
    def test_should_set_project_path(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        assert core.project_path == tmp_path

    def test_should_initialize_sdk_clients_as_empty_dict(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        assert core._sdk_clients == {}

    def test_should_initialize_sdk_clients_connected_as_empty_set(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        assert core._sdk_clients_connected == set()

    def test_should_initialize_locked_tools_as_empty_dict(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        assert core._locked_tools == {}

    def test_should_initialize_interrupt_event(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        assert isinstance(core._interrupt_event, threading.Event)
        assert not core._interrupt_event.is_set()

    def test_should_initialize_sdk_event_callback_as_none(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        assert core._sdk_event_callback is None
        assert core._sdk_session_id is None
        assert core._sdk_node_id is None

    def test_should_set_sdk_providers_class_attribute(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        assert "anthropic" in core._SDK_PROVIDERS


# ---------------------------------------------------------------------------
# OrchestratorCore.request_interrupt / clear_interrupt
# ---------------------------------------------------------------------------


class TestInterruptSignal:
    def test_should_set_interrupt_event(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        core.request_interrupt()
        assert core._interrupt_event.is_set()

    def test_should_clear_interrupt_event(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        core.request_interrupt()
        core.clear_interrupt()
        assert not core._interrupt_event.is_set()


# ---------------------------------------------------------------------------
# OrchestratorCore.set_sdk_event_callback / clear_sdk_event_callback
# ---------------------------------------------------------------------------


class TestSdkEventCallback:
    def test_should_store_callback_and_ids(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        cb = MagicMock()
        core.set_sdk_event_callback(cb, session_id="sess-1", node_id="node-1")
        assert core._sdk_event_callback is cb
        assert core._sdk_session_id == "sess-1"
        assert core._sdk_node_id == "node-1"

    def test_should_clear_callback_and_ids(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        cb = MagicMock()
        core.set_sdk_event_callback(cb, session_id="sess-1", node_id="node-1")
        core.clear_sdk_event_callback()
        assert core._sdk_event_callback is None
        assert core._sdk_session_id is None
        assert core._sdk_node_id is None

    def test_emit_sdk_event_calls_callback(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        cb = MagicMock()
        core.set_sdk_event_callback(cb, session_id="sess-1", node_id="node-1")
        fake_event = SimpleNamespace(event_type="test_event")
        core._emit_sdk_event(fake_event)
        cb.assert_called_once_with(fake_event)

    def test_emit_sdk_event_does_not_raise_when_callback_is_none(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        # No callback set — should be a no-op without raising
        fake_event = SimpleNamespace(event_type="test_event")
        core._emit_sdk_event(fake_event)  # must not raise

    def test_emit_sdk_event_swallows_callback_exception(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        cb = MagicMock(side_effect=RuntimeError("boom"))
        core.set_sdk_event_callback(cb, session_id="s", node_id="n")
        fake_event = SimpleNamespace(event_type="crash")
        # Should not propagate the RuntimeError
        core._emit_sdk_event(fake_event)


# ---------------------------------------------------------------------------
# OrchestratorCore._build_query_options
# ---------------------------------------------------------------------------


class TestBuildQueryOptions:
    def _make_core_with_build_sdk_options(
        self,
        tmp_path: Path,
    ) -> tuple[OrchestratorCore, MagicMock]:
        """Return a core instance with build_sdk_options patched so we can inspect kwargs."""
        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir(parents=True, exist_ok=True)

        mock_build_sdk = MagicMock(return_value=MagicMock())
        mock_registry = MagicMock()
        mock_registry.get_agent_definition.return_value = None  # no agent tools by default

        with (
            patch("pixl.orchestration.core.BacklogStore"),
            patch("pixl.orchestration.core.BoulderStore"),
            patch("pixl.orchestration.core.ConfigStore"),
            patch("pixl.orchestration.core.load_providers_config") as mock_lpc,
            patch("pixl.orchestration.core.ProviderRegistry"),
            patch("pixl.orchestration.core.ConcurrencyManager"),
            patch("pixl.orchestration.core.BackgroundManager"),
            patch("pixl.orchestration.core.AgentRegistry", return_value=mock_registry),
            patch("pixl.orchestration.core._resolve_crew_plugin_path", return_value=None),
            patch("pixl.orchestration.core.build_sdk_options", mock_build_sdk),
        ):
            providers_cfg = MagicMock()
            providers_cfg.concurrency = MagicMock()
            providers_cfg.parse_model_string.return_value = (None, None)
            mock_lpc.return_value = providers_cfg
            core = OrchestratorCore(project_path=tmp_path)

        # Patch _resolve_model to be an identity function for simplicity
        core._resolve_model = lambda m: m  # type: ignore[method-assign]
        core.agent_registry = mock_registry

        return core, mock_build_sdk

    def test_should_call_build_sdk_options_with_model(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)
        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options(model="claude-haiku-4-5")
        mock_build.assert_called_once()
        kwargs = mock_build.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5"

    def test_should_pass_max_turns_to_build_sdk_options(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)
        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options(max_turns=99)
        kwargs = mock_build.call_args.kwargs
        assert kwargs["max_turns"] == 99

    def test_should_set_enable_safety_hooks_true(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)
        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options()
        kwargs = mock_build.call_args.kwargs
        assert kwargs["enable_safety_hooks"] is True

    def test_should_pass_system_prompt_when_provided(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)
        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options(system_prompt="You are a helper.")
        kwargs = mock_build.call_args.kwargs
        assert kwargs["system_prompt"] == "You are a helper."

    def test_should_pass_cwd_or_project_path_as_fallback(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)
        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options(cwd=None)
        kwargs = mock_build.call_args.kwargs
        # When cwd is None, should fall back to project_path
        assert kwargs["cwd"] == tmp_path

    def test_should_set_allowed_tools_from_agent_registry(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)

        agent_def = MagicMock()
        agent_def.tools = ["Read", "Write"]
        core.agent_registry.get_agent_definition.return_value = agent_def

        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options(agent_name="backend-engineer")

        kwargs = mock_build.call_args.kwargs
        assert set(kwargs["allowed_tools"]) == {"Read", "Write"}

    def test_should_set_allowed_tools_none_when_no_agent_name(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)
        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options(agent_name=None)
        kwargs = mock_build.call_args.kwargs
        assert kwargs["allowed_tools"] is None

    def test_should_pass_fork_session_flag(self, tmp_path: Path) -> None:
        core, mock_build = self._make_core_with_build_sdk_options(tmp_path)
        with patch("pixl.orchestration.core.build_sdk_options", mock_build):
            core._build_query_options(fork_session=True)
        kwargs = mock_build.call_args.kwargs
        assert kwargs["fork_session"] is True


# ---------------------------------------------------------------------------
# OrchestratorCore._get_or_create_client
# ---------------------------------------------------------------------------


class TestGetOrCreateClient:
    async def test_should_create_new_client_on_first_call(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        mock_options = MagicMock()
        mock_options.allowed_tools = ["Read"]

        mock_client = MagicMock()
        with patch("pixl.orchestration.core.ClaudeSDKClient", return_value=mock_client) as mock_cls:
            result = await core._get_or_create_client("agent-x", "claude-sonnet-4-6", mock_options)

        mock_cls.assert_called_once_with(options=mock_options)
        assert result is mock_client
        assert ("agent-x", "claude-sonnet-4-6") in core._sdk_clients

    async def test_should_return_existing_client_on_second_call(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        mock_options = MagicMock()
        mock_options.allowed_tools = ["Read"]

        with patch("pixl.orchestration.core.ClaudeSDKClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            first = await core._get_or_create_client("agent-x", "claude-sonnet-4-6", mock_options)
            second = await core._get_or_create_client("agent-x", "claude-sonnet-4-6", mock_options)

        # Constructor should only be called once
        assert mock_cls.call_count == 1
        assert first is second

    async def test_should_key_by_default_when_agent_name_is_none(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        mock_options = MagicMock()
        mock_options.allowed_tools = None

        with patch("pixl.orchestration.core.ClaudeSDKClient", return_value=MagicMock()):
            await core._get_or_create_client(None, "claude-haiku-4-5", mock_options)

        assert ("_default", "claude-haiku-4-5") in core._sdk_clients

    async def test_should_expand_locked_tools_when_new_stage_requests_extra(
        self, tmp_path: Path
    ) -> None:
        """T-29: Extra tools should be unioned into the locked set, not ignored."""
        core = _make_core(tmp_path)
        key = ("agent-x", "claude-sonnet-4-6")

        # First call: establish client with initial tools
        opts1 = MagicMock()
        opts1.allowed_tools = ["Read", "Write"]
        with patch("pixl.orchestration.core.ClaudeSDKClient", return_value=MagicMock()):
            await core._get_or_create_client("agent-x", "claude-sonnet-4-6", opts1)

        assert set(core._locked_tools[key]) == {"Read", "Write"}

        # Second call: stage requests extra tools (Edit, Bash)
        opts2 = MagicMock()
        opts2.allowed_tools = ["Read", "Edit", "Bash"]
        with patch("pixl.orchestration.core.ClaudeSDKClient"):
            await core._get_or_create_client("agent-x", "claude-sonnet-4-6", opts2)

        # Locked set should be the union
        assert set(core._locked_tools[key]) == {"Read", "Write", "Edit", "Bash"}

    async def test_should_preserve_original_tools_after_expansion(
        self, tmp_path: Path
    ) -> None:
        """T-29: Original locked tools must still be present after expansion."""
        core = _make_core(tmp_path)
        key = ("agent-y", "claude-haiku-4-5")

        opts1 = MagicMock()
        opts1.allowed_tools = ["Read", "Glob"]
        with patch("pixl.orchestration.core.ClaudeSDKClient", return_value=MagicMock()):
            await core._get_or_create_client("agent-y", "claude-haiku-4-5", opts1)

        original_tools = set(core._locked_tools[key])

        opts2 = MagicMock()
        opts2.allowed_tools = ["Grep", "Bash"]
        with patch("pixl.orchestration.core.ClaudeSDKClient"):
            await core._get_or_create_client("agent-y", "claude-haiku-4-5", opts2)

        # Every original tool must still be in the expanded set
        expanded = set(core._locked_tools[key])
        assert original_tools.issubset(expanded)
        assert expanded == {"Read", "Glob", "Grep", "Bash"}

    async def test_should_log_info_when_expanding_tools(self, tmp_path: Path) -> None:
        """T-29: Expansion should be logged at INFO level for observability."""
        core = _make_core(tmp_path)

        opts1 = MagicMock()
        opts1.allowed_tools = ["Read"]
        with patch("pixl.orchestration.core.ClaudeSDKClient", return_value=MagicMock()):
            await core._get_or_create_client("agent-z", "claude-sonnet-4-6", opts1)

        opts2 = MagicMock()
        opts2.allowed_tools = ["Read", "Write"]
        with (
            patch("pixl.orchestration.core.ClaudeSDKClient"),
            patch("pixl.orchestration.core.logger") as mock_logger,
        ):
            await core._get_or_create_client("agent-z", "claude-sonnet-4-6", opts2)

        # Verify logger.info was called with the expansion message
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert any("expanding locked tools" in str(call) for call in info_calls), (
            f"Expected 'expanding locked tools' in logger.info calls: {info_calls}"
        )

    async def test_should_not_expand_when_tools_are_subset(self, tmp_path: Path) -> None:
        """No expansion when new tools are a subset of the locked set."""
        core = _make_core(tmp_path)
        key = ("agent-s", "claude-sonnet-4-6")

        opts1 = MagicMock()
        opts1.allowed_tools = ["Read", "Write", "Edit"]
        with patch("pixl.orchestration.core.ClaudeSDKClient", return_value=MagicMock()):
            await core._get_or_create_client("agent-s", "claude-sonnet-4-6", opts1)

        # Second call with a subset of tools — no expansion needed
        opts2 = MagicMock()
        opts2.allowed_tools = ["Read", "Write"]
        with patch("pixl.orchestration.core.ClaudeSDKClient"):
            await core._get_or_create_client("agent-s", "claude-sonnet-4-6", opts2)

        # Locked set should be unchanged (still the original 3 tools)
        assert set(core._locked_tools[key]) == {"Read", "Write", "Edit"}


# ---------------------------------------------------------------------------
# OrchestratorCore.cleanup_sdk_clients
# ---------------------------------------------------------------------------


class TestCleanupSdkClients:
    async def test_should_clear_all_client_state(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        key = ("agent-a", "claude-sonnet-4-6")
        mock_client = MagicMock()
        mock_client.disconnect = MagicMock(return_value=None)
        core._sdk_clients[key] = mock_client
        core._locked_tools[key] = ["Read"]

        await core.cleanup_sdk_clients()

        assert core._sdk_clients == {}
        assert core._sdk_clients_connected == set()
        assert core._locked_tools == {}

    async def test_should_not_raise_when_disconnect_fails(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        key = ("agent-b", "claude-haiku-4-5")
        mock_client = MagicMock()

        async def _bad_disconnect() -> None:
            raise RuntimeError("network gone")

        mock_client.disconnect = _bad_disconnect
        core._sdk_clients[key] = mock_client
        core._sdk_clients_connected.add(key)

        # Should complete without propagating the error
        await core.cleanup_sdk_clients()
        assert core._sdk_clients == {}


# ---------------------------------------------------------------------------
# OrchestratorCore._process_streaming_message — circuit breaker path
# ---------------------------------------------------------------------------


class TestProcessStreamingMessageCircuitBreaker:
    def _make_error_block(self, text: str) -> Any:
        block = SimpleNamespace(text=text)
        return block

    async def test_should_increment_error_count_on_unrecoverable_pattern(
        self, tmp_path: Path
    ) -> None:
        core = _make_core(tmp_path)
        error_text = "tool_use.name: String should have at most 64 characters"
        message = SimpleNamespace(content=[self._make_error_block(error_text)])

        # Patch _emit_sdk_events_for_message and _stream_message so they don't fail
        core._emit_sdk_events_for_message = MagicMock()  # type: ignore[method-assign]
        core._stream_message = MagicMock()  # type: ignore[method-assign]

        with patch("pixl.orchestration.core.is_json_mode", return_value=True):
            count, _, _, aborted = await core._process_streaming_message(
                message,
                sdk_result_ref=[None],
                stream_callback=None,
                api_error_count=0,
                result_text="",
            )

        assert count == 1
        assert aborted is False

    async def test_should_abort_when_circuit_breaker_threshold_reached(
        self, tmp_path: Path
    ) -> None:
        from pixl.orchestration.core import _API_ERROR_CIRCUIT_BREAKER

        core = _make_core(tmp_path)
        error_text = "tool_use.name: String should have at most 64 characters"
        message = SimpleNamespace(content=[self._make_error_block(error_text)])

        core._emit_sdk_events_for_message = MagicMock()  # type: ignore[method-assign]
        core._stream_message = MagicMock()  # type: ignore[method-assign]

        # Start at threshold so the next increment triggers the breaker
        with patch("pixl.orchestration.core.is_json_mode", return_value=True):
            count, _, error_msg, aborted = await core._process_streaming_message(
                message,
                sdk_result_ref=[None],
                stream_callback=None,
                api_error_count=_API_ERROR_CIRCUIT_BREAKER - 1,
                result_text="",
            )

        assert aborted is True
        assert error_msg is not None
        assert "Unrecoverable API error" in error_msg

    async def test_should_abort_immediately_on_interrupt_event(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        core._interrupt_event.set()

        message = SimpleNamespace()  # no content attribute

        _, _, error_msg, aborted = await core._process_streaming_message(
            message,
            sdk_result_ref=[None],
            stream_callback=None,
            api_error_count=0,
            result_text="",
        )

        assert aborted is True
        assert error_msg is not None
        assert "interrupted" in error_msg.lower()
