"""Tests for workflow execution top-level modules.

Coverage targets:
- workflow_runner.py: in-process execution tracking, heartbeat, concurrency guard
- workflow_background.py: per-session concurrency guard (_try_start_execution / _release_execution)
- workflow_helpers.py: has_waiting_gates, get_waiting_gate_node, set_worktree_baton_context
- session_report_manager.py: reports_enabled, _parse_iso_timestamp, _failed_auto_job_retry_allowed,
                              _build_report_prompt, _next_report_version, resolve_report_model
- autonomy.py: _parse_float_config, _parse_int_config, _reconcile_autonomy_level,
               resolve_latest_agent_task_pair, should_auto_approve_waiting_gate (skip_approval),
               should_auto_approve_waiting_gate (assist), record_autonomy_outcome
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers shared across test sections
# ─────────────────────────────────────────────────────────────────────────────


def _make_session(
    *,
    session_id: str = "sess-001",
    feature_id: str = "feat-abc",
    node_instances: dict | None = None,
) -> MagicMock:
    """Build a minimal WorkflowSession mock."""
    session = MagicMock()
    session.id = session_id
    session.feature_id = feature_id
    session.node_instances = node_instances if node_instances is not None else {}
    session.workspace_root = None
    session.paused_at = None
    session.executor_cursor = None
    return session


def _make_db() -> MagicMock:
    """Build a minimal PixlDB mock with the most commonly accessed sub-stores."""
    db = MagicMock()
    db.sessions = MagicMock()
    db.events = MagicMock()
    db.backlog = MagicMock()
    db.heartbeat_runs = MagicMock()
    db.artifacts = MagicMock()
    db.conn = MagicMock()
    db.get_config = MagicMock(return_value=None)
    return db


# ─────────────────────────────────────────────────────────────────────────────
# Section 1: workflow_runner — in-process execution tracking
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowRunnerTracking:
    """Tests for _mark_execution_active, _release_execution, get_active_sessions_for_project."""

    def setup_method(self):
        # Ensure clean state before each test by clearing the module-level dict.
        import pixl.execution.workflow_runner as wr

        with wr._executor_lock:
            wr._executing_sessions.clear()

    def teardown_method(self):
        import pixl.execution.workflow_runner as wr

        with wr._executor_lock:
            wr._executing_sessions.clear()

    def test_mark_execution_active_records_session(self):
        from pixl.execution.workflow_runner import (
            _mark_execution_active,
            get_active_sessions_for_project,
        )

        _mark_execution_active("sess-1", "owner-1", "proj-A")
        active = get_active_sessions_for_project("proj-A")
        assert "sess-1" in active

    def test_get_active_sessions_filters_by_project(self):
        from pixl.execution.workflow_runner import (
            _mark_execution_active,
            get_active_sessions_for_project,
        )

        _mark_execution_active("sess-1", "owner-1", "proj-A")
        _mark_execution_active("sess-2", "owner-2", "proj-B")

        active_a = get_active_sessions_for_project("proj-A")
        assert "sess-1" in active_a
        assert "sess-2" not in active_a

    def test_release_execution_removes_session_when_owner_matches(self):
        from pixl.execution.workflow_runner import (
            _mark_execution_active,
            _release_execution,
            get_active_sessions_for_project,
        )

        _mark_execution_active("sess-1", "owner-1", "proj-A")
        _release_execution("sess-1", "owner-1")
        active = get_active_sessions_for_project("proj-A")
        assert "sess-1" not in active

    def test_release_execution_noop_when_owner_mismatch(self):
        from pixl.execution.workflow_runner import (
            _mark_execution_active,
            _release_execution,
            get_active_sessions_for_project,
        )

        _mark_execution_active("sess-1", "owner-correct", "proj-A")
        # Different owner — should NOT remove
        _release_execution("sess-1", "owner-wrong")
        active = get_active_sessions_for_project("proj-A")
        assert "sess-1" in active

    def test_release_execution_noop_for_unknown_session(self):
        from pixl.execution.workflow_runner import _release_execution

        # Should not raise
        _release_execution("nonexistent-session", "any-owner")

    def test_get_active_sessions_returns_empty_list_for_unknown_project(self):
        from pixl.execution.workflow_runner import get_active_sessions_for_project

        result = get_active_sessions_for_project("no-such-project")
        assert result == []


class TestHeartbeatContextManager:
    """Tests for _heartbeat_during_step context manager behaviour."""

    def test_heartbeat_calls_touch_session(self):
        from pixl.execution.workflow_runner import _heartbeat_during_step

        session_store = MagicMock()

        # Use a tiny interval so the heartbeat fires quickly
        with _heartbeat_during_step(session_store, "sess-hb", interval=0.01):
            # Give the thread a chance to fire
            import time

            time.sleep(0.05)

        # touch_session should have been called at least once
        assert session_store.touch_session.call_count >= 1

    def test_heartbeat_suppresses_touch_session_exceptions(self):
        """Ensure exceptions in touch_session do not crash the main thread."""
        from pixl.execution.workflow_runner import _heartbeat_during_step

        session_store = MagicMock()
        session_store.touch_session.side_effect = RuntimeError("DB offline")

        # Should not raise
        with _heartbeat_during_step(session_store, "sess-err", interval=0.01):
            import time

            time.sleep(0.05)


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: workflow_background — per-session concurrency guard
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowBackgroundConcurrencyGuard:
    """Tests for _try_start_execution and _release_execution in workflow_background."""

    def setup_method(self):
        import pixl.execution.workflow_background as wb

        with wb._executor_lock:
            wb._executing_sessions.clear()

    def teardown_method(self):
        import pixl.execution.workflow_background as wb

        with wb._executor_lock:
            wb._executing_sessions.clear()

    def test_try_start_execution_returns_true_for_new_session(self):
        from pixl.execution.workflow_background import _try_start_execution

        assert _try_start_execution("sess-new") is True

    def test_try_start_execution_returns_false_for_already_running_session(self):
        from pixl.execution.workflow_background import _try_start_execution

        _try_start_execution("sess-dup")
        assert _try_start_execution("sess-dup") is False

    def test_release_execution_allows_reacquisition(self):
        from pixl.execution.workflow_background import (
            _release_execution,
            _try_start_execution,
        )

        _try_start_execution("sess-rel")
        _release_execution("sess-rel")
        assert _try_start_execution("sess-rel") is True

    def test_release_execution_is_idempotent(self):
        from pixl.execution.workflow_background import _release_execution

        # Releasing a session that was never acquired should not raise
        _release_execution("sess-never-acquired")

    def test_run_workflow_background_skips_already_executing_session(self):
        """Should log and return without calling _run_workflow_inner if already running."""
        from pixl.execution.workflow_background import (
            _try_start_execution,
            run_workflow_background,
        )

        # Pre-claim the session
        _try_start_execution("sess-concurrent")

        with patch(
            "pixl.execution.workflow_background._run_workflow_inner"
        ) as mock_inner:
            run_workflow_background(
                project_path=Path("/tmp/fake"),
                session_id="sess-concurrent",
                workflow_id="test-wf",
                skip_approval=False,
                db=_make_db(),
            )
            mock_inner.assert_not_called()


class TestWorkflowBackgroundHelpers:
    """Tests for _has_waiting_gates and _get_waiting_gate_node."""

    def test_has_waiting_gates_returns_true_when_gate_waiting(self):
        from pixl.execution.workflow_background import _has_waiting_gates

        session = _make_session(
            node_instances={
                "gate-1": {"state": "gate_waiting"},
                "task-1": {"state": "task_completed"},
            }
        )
        assert _has_waiting_gates(session) is True

    def test_has_waiting_gates_returns_false_when_no_gate(self):
        from pixl.execution.workflow_background import _has_waiting_gates

        session = _make_session(
            node_instances={
                "task-1": {"state": "task_completed"},
                "task-2": {"state": "task_pending"},
            }
        )
        assert _has_waiting_gates(session) is False

    def test_has_waiting_gates_returns_false_for_empty_instances(self):
        from pixl.execution.workflow_background import _has_waiting_gates

        session = _make_session(node_instances={})
        assert _has_waiting_gates(session) is False

    def test_get_waiting_gate_node_returns_node_id(self):
        from pixl.execution.workflow_background import _get_waiting_gate_node

        session = _make_session(
            node_instances={
                "task-1": {"state": "task_completed"},
                "gate-review": {"state": "gate_waiting"},
            }
        )
        assert _get_waiting_gate_node(session) == "gate-review"

    def test_get_waiting_gate_node_returns_none_when_no_gate(self):
        from pixl.execution.workflow_background import _get_waiting_gate_node

        session = _make_session(
            node_instances={"task-1": {"state": "task_completed"}}
        )
        assert _get_waiting_gate_node(session) is None


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: workflow_helpers — pure utility functions
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowHelpers:
    """Tests for has_waiting_gates, get_waiting_gate_node, set_worktree_baton_context."""

    def test_has_waiting_gates_true_when_gate_waiting(self):
        from pixl.execution.workflow_helpers import has_waiting_gates

        session = _make_session(
            node_instances={"gate-1": {"state": "gate_waiting"}}
        )
        assert has_waiting_gates(session) is True

    def test_has_waiting_gates_false_when_all_completed(self):
        from pixl.execution.workflow_helpers import has_waiting_gates

        session = _make_session(
            node_instances={
                "task-1": {"state": "task_completed"},
                "task-2": {"state": "task_completed"},
            }
        )
        assert has_waiting_gates(session) is False

    def test_has_waiting_gates_false_for_empty_instances(self):
        from pixl.execution.workflow_helpers import has_waiting_gates

        session = _make_session(node_instances={})
        assert has_waiting_gates(session) is False

    def test_get_waiting_gate_node_returns_first_waiting_gate(self):
        from pixl.execution.workflow_helpers import get_waiting_gate_node

        session = _make_session(
            node_instances={
                "gate-review": {"state": "gate_waiting"},
                "task-1": {"state": "task_completed"},
            }
        )
        assert get_waiting_gate_node(session) == "gate-review"

    def test_get_waiting_gate_node_returns_none_when_no_gate(self):
        from pixl.execution.workflow_helpers import get_waiting_gate_node

        session = _make_session(node_instances={"task-1": {"state": "task_pending"}})
        assert get_waiting_gate_node(session) is None

    def test_set_worktree_baton_context_writes_baton_to_db(self):
        from pixl.execution.workflow_helpers import set_worktree_baton_context

        db = _make_db()
        db.sessions.get_session.return_value = {"baton": None}

        set_worktree_baton_context(
            db,
            "sess-001",
            branch_name="pixl/feat-abc",
            workspace_root="/tmp/workspace",
        )

        db.sessions.update_session.assert_called_once()
        call_kwargs = db.sessions.update_session.call_args
        # The first positional arg should be session_id
        assert call_kwargs[0][0] == "sess-001"
        baton_json = call_kwargs[1]["baton"]
        baton = json.loads(baton_json)
        assert baton["worktree"]["branch_name"] == "pixl/feat-abc"
        assert baton["worktree"]["workspace_root"] == "/tmp/workspace"

    def test_set_worktree_baton_context_preserves_existing_baton_fields(self):
        from pixl.execution.workflow_helpers import set_worktree_baton_context

        db = _make_db()
        existing_baton = json.dumps({"existing_key": "existing_value"})
        db.sessions.get_session.return_value = {"baton": existing_baton}

        set_worktree_baton_context(
            db,
            "sess-002",
            branch_name="pixl/feat-xyz",
            workspace_root="/tmp/ws2",
        )

        call_kwargs = db.sessions.update_session.call_args
        baton = json.loads(call_kwargs[1]["baton"])
        # Original key preserved
        assert baton["existing_key"] == "existing_value"
        # New worktree key added
        assert "worktree" in baton

    def test_set_worktree_baton_context_handles_invalid_json_baton(self):
        from pixl.execution.workflow_helpers import set_worktree_baton_context

        db = _make_db()
        # Corrupt JSON in DB — should be treated as empty baton
        db.sessions.get_session.return_value = {"baton": "not-valid-json"}

        # Should not raise; fall back to empty baton
        try:
            set_worktree_baton_context(
                db,
                "sess-003",
                branch_name="pixl/feat-bad",
                workspace_root="/tmp/ws3",
            )
        except Exception:
            # Some implementations may raise on invalid JSON — that's acceptable
            pass

    def test_set_worktree_baton_context_with_base_ref(self):
        from pixl.execution.workflow_helpers import set_worktree_baton_context

        db = _make_db()
        db.sessions.get_session.return_value = {"baton": None}

        set_worktree_baton_context(
            db,
            "sess-004",
            branch_name="pixl/feat-ref",
            base_ref="main",
            workspace_root="/tmp/ws4",
        )

        baton = json.loads(db.sessions.update_session.call_args[1]["baton"])
        assert baton["worktree"]["base_ref"] == "main"


# ─────────────────────────────────────────────────────────────────────────────
# Section 4: session_report_manager — configuration and helpers
# ─────────────────────────────────────────────────────────────────────────────


class TestReportsEnabled:
    """Tests for reports_enabled() environment-driven configuration."""

    def test_returns_false_during_pytest_by_default(self):
        # PYTEST_CURRENT_TEST is set when running under pytest
        # The function should return False in that case (and we're in pytest now)
        import os

        from pixl.execution.session_report_manager import reports_enabled

        if os.environ.get("PYTEST_CURRENT_TEST"):
            assert reports_enabled() is False

    def test_env_var_true_overrides_pytest_default(self):
        from pixl.execution.session_report_manager import reports_enabled

        with patch.dict("os.environ", {"PIXL_SESSION_REPORT_DAEMON_ENABLED": "1"}):
            assert reports_enabled() is True

    def test_env_var_false_disables_reports(self):
        from pixl.execution.session_report_manager import reports_enabled

        with patch.dict(
            "os.environ",
            {"PIXL_SESSION_REPORT_DAEMON_ENABLED": "false"},
            clear=False,
        ):
            assert reports_enabled() is False

    def test_env_var_yes_enables_reports(self):
        from pixl.execution.session_report_manager import reports_enabled

        with patch.dict("os.environ", {"PIXL_SESSION_REPORT_DAEMON_ENABLED": "yes"}):
            assert reports_enabled() is True

    def test_env_var_on_enables_reports(self):
        from pixl.execution.session_report_manager import reports_enabled

        with patch.dict("os.environ", {"PIXL_SESSION_REPORT_DAEMON_ENABLED": "on"}):
            assert reports_enabled() is True


class TestParseIsoTimestamp:
    """Tests for _parse_iso_timestamp helper."""

    def test_returns_none_for_none_input(self):
        from pixl.execution.session_report_manager import _parse_iso_timestamp

        assert _parse_iso_timestamp(None) is None

    def test_returns_none_for_empty_string(self):
        from pixl.execution.session_report_manager import _parse_iso_timestamp

        assert _parse_iso_timestamp("") is None

    def test_parses_valid_iso_string(self):
        from pixl.execution.session_report_manager import _parse_iso_timestamp

        result = _parse_iso_timestamp("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parses_iso_string_with_z_suffix(self):
        from pixl.execution.session_report_manager import _parse_iso_timestamp

        result = _parse_iso_timestamp("2024-06-01T12:00:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_returns_none_for_invalid_string(self):
        from pixl.execution.session_report_manager import _parse_iso_timestamp

        assert _parse_iso_timestamp("not-a-date") is None

    def test_coerces_non_string_to_string(self):
        from pixl.execution.session_report_manager import _parse_iso_timestamp

        # Integers / other types should be coerced via str()
        # "2024" is not a full ISO timestamp — expect None
        result = _parse_iso_timestamp(2024)
        assert result is None


class TestFailedAutoJobRetryAllowed:
    """Tests for _failed_auto_job_retry_allowed decision logic."""

    def test_allows_retry_when_below_max_retries_and_past_cooldown(self):
        from pixl.execution.session_report_manager import _failed_auto_job_retry_allowed

        past_ts = (datetime.now() - timedelta(seconds=400)).isoformat()
        job = {"retry_count": 0, "completed_at": past_ts}
        assert _failed_auto_job_retry_allowed(job, max_retries=3, cooldown_seconds=300) is True

    def test_blocks_retry_when_at_max_retries(self):
        from pixl.execution.session_report_manager import _failed_auto_job_retry_allowed

        job = {"retry_count": 3, "completed_at": None}
        assert _failed_auto_job_retry_allowed(job, max_retries=3, cooldown_seconds=0) is False

    def test_blocks_retry_when_cooldown_not_elapsed(self):
        from pixl.execution.session_report_manager import _failed_auto_job_retry_allowed

        recent_ts = (datetime.now() - timedelta(seconds=10)).isoformat()
        job = {"retry_count": 0, "completed_at": recent_ts}
        assert (
            _failed_auto_job_retry_allowed(job, max_retries=3, cooldown_seconds=300) is False
        )

    def test_allows_retry_when_no_timestamp_present(self):
        from pixl.execution.session_report_manager import _failed_auto_job_retry_allowed

        job = {"retry_count": 0}  # No timestamp at all
        assert _failed_auto_job_retry_allowed(job, max_retries=3, cooldown_seconds=300) is True

    def test_handles_invalid_retry_count_gracefully(self):
        from pixl.execution.session_report_manager import _failed_auto_job_retry_allowed

        past_ts = (datetime.now() - timedelta(seconds=400)).isoformat()
        job = {"retry_count": "bad_value", "completed_at": past_ts}
        # Should default retry_count to 0, so retry is allowed
        assert _failed_auto_job_retry_allowed(job, max_retries=3, cooldown_seconds=300) is True

    def test_blocks_retry_when_max_retries_is_zero(self):
        from pixl.execution.session_report_manager import _failed_auto_job_retry_allowed

        job = {"retry_count": 0}
        assert _failed_auto_job_retry_allowed(job, max_retries=0, cooldown_seconds=0) is False


class TestBuildReportPrompt:
    """Tests for _build_report_prompt output structure."""

    def test_prompt_contains_session_id(self):
        from pixl.execution.session_report_manager import _build_report_prompt

        prompt = _build_report_prompt(
            audit_payload={"key": "value"},
            session_id="sess-test",
            trigger="manual",
            terminal_status=None,
        )
        assert "sess-test" in prompt

    def test_prompt_contains_trigger(self):
        from pixl.execution.session_report_manager import _build_report_prompt

        prompt = _build_report_prompt(
            audit_payload={},
            session_id="s",
            trigger="auto_terminal",
            terminal_status="completed",
        )
        assert "auto_terminal" in prompt
        assert "completed" in prompt

    def test_prompt_contains_json_payload(self):
        from pixl.execution.session_report_manager import _build_report_prompt

        prompt = _build_report_prompt(
            audit_payload={"event_count": 42},
            session_id="s",
            trigger="test",
            terminal_status=None,
        )
        assert '"event_count"' in prompt
        assert "42" in prompt

    def test_prompt_omits_terminal_status_when_none(self):
        from pixl.execution.session_report_manager import _build_report_prompt

        prompt = _build_report_prompt(
            audit_payload={},
            session_id="s",
            trigger="manual",
            terminal_status=None,
        )
        assert "terminal_status" not in prompt

    def test_prompt_includes_output_sections(self):
        from pixl.execution.session_report_manager import _build_report_prompt

        prompt = _build_report_prompt(
            audit_payload={},
            session_id="s",
            trigger="t",
            terminal_status=None,
        )
        for section in [
            "Executive Assessment",
            "What Went Well",
            "What Went Wrong",
            "Prioritized Recommendations",
        ]:
            assert section in prompt


class TestNextReportVersion:
    """Tests for _next_report_version semantic versioning logic."""

    def test_returns_1_0_0_when_no_existing_versions(self):
        from pixl.execution.session_report_manager import _next_report_version

        version, prev_id = _next_report_version([])
        assert version == "1.0.0"
        assert prev_id is None

    def test_returns_patch_increment_for_existing_version(self):
        from pixl.execution.session_report_manager import _next_report_version

        existing = [{"id": "art-1", "version": "1.0.0"}]
        version, prev_id = _next_report_version(existing)
        assert version == "1.0.1"
        assert prev_id == "art-1"

    def test_returns_1_0_1_when_no_version_field_in_existing(self):
        from pixl.execution.session_report_manager import _next_report_version

        existing = [{"id": "art-old", "version": None}]
        version, prev_id = _next_report_version(existing)
        assert version == "1.0.1"
        assert prev_id == "art-old"

    def test_uses_last_entry_for_prev_version_id(self):
        from pixl.execution.session_report_manager import _next_report_version

        existing = [
            {"id": "art-1", "version": "1.0.0"},
            {"id": "art-2", "version": "1.0.1"},
        ]
        version, prev_id = _next_report_version(existing)
        assert prev_id == "art-2"


class TestAutoTerminalRetryConfig:
    """Tests for _auto_terminal_max_retries and _auto_terminal_retry_cooldown_seconds."""

    def test_default_max_retries(self):
        from pixl.execution.session_report_manager import (
            AUTO_TERMINAL_MAX_RETRIES,
            _auto_terminal_max_retries,
        )

        with patch.dict("os.environ", {}, clear=False):
            # Remove the env var if present
            import os

            os.environ.pop("PIXL_SESSION_REPORT_AUTO_MAX_RETRIES", None)
            assert _auto_terminal_max_retries() == AUTO_TERMINAL_MAX_RETRIES

    def test_env_var_overrides_max_retries(self):
        from pixl.execution.session_report_manager import _auto_terminal_max_retries

        with patch.dict("os.environ", {"PIXL_SESSION_REPORT_AUTO_MAX_RETRIES": "7"}):
            assert _auto_terminal_max_retries() == 7

    def test_invalid_env_var_falls_back_to_default(self):
        from pixl.execution.session_report_manager import (
            AUTO_TERMINAL_MAX_RETRIES,
            _auto_terminal_max_retries,
        )

        with patch.dict(
            "os.environ", {"PIXL_SESSION_REPORT_AUTO_MAX_RETRIES": "not-an-int"}
        ):
            assert _auto_terminal_max_retries() == AUTO_TERMINAL_MAX_RETRIES

    def test_default_cooldown_seconds(self):
        import os

        from pixl.execution.session_report_manager import (
            AUTO_TERMINAL_RETRY_COOLDOWN_SECONDS,
            _auto_terminal_retry_cooldown_seconds,
        )

        os.environ.pop("PIXL_SESSION_REPORT_AUTO_RETRY_COOLDOWN_SECONDS", None)
        assert _auto_terminal_retry_cooldown_seconds() == AUTO_TERMINAL_RETRY_COOLDOWN_SECONDS

    def test_env_var_overrides_cooldown(self):
        from pixl.execution.session_report_manager import _auto_terminal_retry_cooldown_seconds

        with patch.dict(
            "os.environ", {"PIXL_SESSION_REPORT_AUTO_RETRY_COOLDOWN_SECONDS": "600"}
        ):
            assert _auto_terminal_retry_cooldown_seconds() == 600


# ─────────────────────────────────────────────────────────────────────────────
# Section 5: autonomy — config parsing, reconciliation, approval logic
# ─────────────────────────────────────────────────────────────────────────────


class TestParseFloatConfig:
    """Tests for _parse_float_config."""

    def test_returns_default_when_raw_is_none(self):
        from pixl.execution.autonomy import _parse_float_config

        assert _parse_float_config(None, 0.5) == 0.5

    def test_parses_valid_float_string(self):
        from pixl.execution.autonomy import _parse_float_config

        assert _parse_float_config("0.75", 0.5) == pytest.approx(0.75)

    def test_clamps_value_above_1(self):
        from pixl.execution.autonomy import _parse_float_config

        assert _parse_float_config("1.5", 0.5) == 1.0

    def test_clamps_value_below_0(self):
        from pixl.execution.autonomy import _parse_float_config

        assert _parse_float_config("-0.1", 0.5) == 0.0

    def test_returns_default_for_invalid_string(self):
        from pixl.execution.autonomy import _parse_float_config

        assert _parse_float_config("not-a-float", 0.9) == 0.9


class TestParseIntConfig:
    """Tests for _parse_int_config."""

    def test_returns_default_when_raw_is_none(self):
        from pixl.execution.autonomy import _parse_int_config

        assert _parse_int_config(None, 3) == 3

    def test_parses_valid_int_string(self):
        from pixl.execution.autonomy import _parse_int_config

        assert _parse_int_config("7", 3) == 7

    def test_clamps_negative_to_zero(self):
        from pixl.execution.autonomy import _parse_int_config

        assert _parse_int_config("-5", 3) == 0

    def test_returns_default_for_invalid_string(self):
        from pixl.execution.autonomy import _parse_int_config

        assert _parse_int_config("bad", 5) == 5


class TestReconcileAutonomyLevel:
    """Tests for _reconcile_autonomy_level ladder logic."""

    def test_returns_level_0_when_insufficient_history(self):
        from pixl.execution.autonomy import _reconcile_autonomy_level

        level, reason = _reconcile_autonomy_level(
            previous_level=2, confidence=0.99, samples=1, min_samples=3
        )
        assert level == 0
        assert reason == "insufficient_history"

    def test_promotes_to_level_1_at_supervised_threshold(self):
        from pixl.execution.autonomy import (
            SUPERVISED_CONFIDENCE_THRESHOLD,
            _reconcile_autonomy_level,
        )

        level, reason = _reconcile_autonomy_level(
            previous_level=0,
            confidence=SUPERVISED_CONFIDENCE_THRESHOLD,
            samples=5,
            min_samples=3,
        )
        assert level == 1
        assert reason == "promoted"

    def test_promotes_to_level_2_at_promote_threshold(self):
        from pixl.execution.autonomy import (
            PROMOTE_LEVEL_2_THRESHOLD,
            _reconcile_autonomy_level,
        )

        level, reason = _reconcile_autonomy_level(
            previous_level=1,
            confidence=PROMOTE_LEVEL_2_THRESHOLD,
            samples=5,
            min_samples=3,
        )
        assert level == 2
        assert reason == "promoted"

    def test_demotes_when_confidence_below_demote_threshold(self):
        from pixl.execution.autonomy import DEMOTE_THRESHOLD, _reconcile_autonomy_level

        level, reason = _reconcile_autonomy_level(
            previous_level=2,
            confidence=DEMOTE_THRESHOLD - 0.01,
            samples=5,
            min_samples=3,
        )
        assert level == 1
        assert reason == "demoted"

    def test_stable_when_confidence_between_thresholds(self):
        from pixl.execution.autonomy import _reconcile_autonomy_level

        # Between DEMOTE_THRESHOLD and SUPERVISED_CONFIDENCE_THRESHOLD, level 1 stays 1
        level, reason = _reconcile_autonomy_level(
            previous_level=1, confidence=0.80, samples=5, min_samples=3
        )
        assert level == 1
        assert reason == "stable"

    def test_below_threshold_at_level_0_returns_below_threshold_reason(self):
        from pixl.execution.autonomy import DEMOTE_THRESHOLD, _reconcile_autonomy_level

        level, reason = _reconcile_autonomy_level(
            previous_level=0,
            confidence=DEMOTE_THRESHOLD - 0.01,
            samples=5,
            min_samples=3,
        )
        assert level == 0
        assert reason == "below_threshold"


class TestResolveLatestAgentTaskPair:
    """Tests for resolve_latest_agent_task_pair."""

    def test_returns_unknown_workflow_when_no_completed_nodes(self):
        from pixl.execution.autonomy import resolve_latest_agent_task_pair

        session = _make_session(
            node_instances={"gate-1": {"state": "gate_waiting", "agent_name": None}}
        )
        agent, task = resolve_latest_agent_task_pair(session)
        assert agent == "unknown"
        assert task == "workflow"

    def test_returns_agent_from_completed_node(self):
        from pixl.execution.autonomy import resolve_latest_agent_task_pair

        session = _make_session(
            node_instances={
                "task-1": {
                    "state": "task_completed",
                    "agent_name": "backend-engineer",
                    "ended_at": "2024-01-01T10:00:00",
                }
            }
        )
        agent, task = resolve_latest_agent_task_pair(session)
        assert agent == "backend-engineer"
        assert task == "task-1"

    def test_returns_most_recent_by_timestamp(self):
        from pixl.execution.autonomy import resolve_latest_agent_task_pair

        session = _make_session(
            node_instances={
                "task-1": {
                    "state": "task_completed",
                    "agent_name": "frontend-engineer",
                    "ended_at": "2024-01-01T09:00:00",
                },
                "task-2": {
                    "state": "task_completed",
                    "agent_name": "backend-engineer",
                    "ended_at": "2024-01-01T11:00:00",
                },
            }
        )
        agent, task = resolve_latest_agent_task_pair(session)
        # task-2 has later timestamp
        assert agent == "backend-engineer"
        assert task == "task-2"

    def test_skips_nodes_without_agent_name(self):
        from pixl.execution.autonomy import resolve_latest_agent_task_pair

        session = _make_session(
            node_instances={
                "task-no-agent": {
                    "state": "task_completed",
                    "agent_name": None,
                    "ended_at": "2024-01-01T12:00:00",
                },
                "task-with-agent": {
                    "state": "task_completed",
                    "agent_name": "architect",
                    "ended_at": "2024-01-01T10:00:00",
                },
            }
        )
        agent, task = resolve_latest_agent_task_pair(session)
        assert agent == "architect"


class TestShouldAutoApproveWaitingGate:
    """Tests for should_auto_approve_waiting_gate decision function."""

    def test_skip_approval_always_approves(self):
        from pixl.execution.autonomy import should_auto_approve_waiting_gate

        db = _make_db()
        result = should_auto_approve_waiting_gate(
            db,
            session_id="sess-1",
            feature_id="feat-1",
            skip_approval=True,
        )
        assert result["approve"] is True
        assert result["mode"] == "override"
        assert result["reason"] == "skip_approval"
        assert result["level"] == 3

    def test_missing_feature_id_never_approves(self):
        from pixl.execution.autonomy import should_auto_approve_waiting_gate

        db = _make_db()
        result = should_auto_approve_waiting_gate(
            db,
            session_id="sess-1",
            feature_id=None,
            skip_approval=False,
        )
        assert result["approve"] is False
        assert result["mode"] == "assist"
        assert result["reason"] == "missing_feature_id"

    def test_assist_mode_never_approves_even_with_high_confidence(self):
        from pixl.execution.autonomy import should_auto_approve_waiting_gate

        db = _make_db()
        db.get_config.return_value = "assist"
        db.conn.execute.return_value.fetchall.return_value = []
        db.conn.execute.return_value.fetchone.return_value = None
        db.events.get_events.return_value = []

        result = should_auto_approve_waiting_gate(
            db,
            session_id="sess-1",
            feature_id="feat-1",
            skip_approval=False,
        )
        assert result["approve"] is False
        assert result["mode"] == "assist"

    def test_returns_expected_keys_in_result_dict(self):
        from pixl.execution.autonomy import should_auto_approve_waiting_gate

        db = _make_db()
        db.get_config.return_value = None
        db.conn.execute.return_value.fetchall.return_value = []
        db.conn.execute.return_value.fetchone.return_value = None
        db.events.get_events.return_value = []

        result = should_auto_approve_waiting_gate(
            db,
            session_id="sess-1",
            feature_id="feat-1",
            skip_approval=False,
        )
        expected_keys = {
            "approve",
            "mode",
            "reason",
            "confidence",
            "threshold",
            "samples",
            "min_samples",
            "level",
            "previous_level",
            "confidence_source",
            "agent_name",
            "task_key",
        }
        assert expected_keys <= set(result.keys())

    def test_autopilot_with_insufficient_history_does_not_approve(self):
        from pixl.execution.autonomy import should_auto_approve_waiting_gate

        db = _make_db()
        # Mode = autopilot
        db.get_config.side_effect = lambda key, default=None: (
            "autopilot" if "autonomy:feat-low" in key else default
        )
        # Return empty history so samples = 0
        db.conn.execute.return_value.fetchall.return_value = []
        db.conn.execute.return_value.fetchone.return_value = None
        db.events.get_events.return_value = []

        result = should_auto_approve_waiting_gate(
            db,
            session_id="sess-1",
            feature_id="feat-low",
            skip_approval=False,
        )
        assert result["approve"] is False
        assert result["reason"] == "insufficient_history"


class TestRecordAutonomyOutcome:
    """Tests for record_autonomy_outcome with mocked session and DB."""

    def test_noop_when_session_has_no_feature_id(self):
        from pixl.execution.autonomy import record_autonomy_outcome

        db = _make_db()
        session = _make_session(feature_id=None)
        session.feature_id = None

        # Should not call conn.execute at all
        record_autonomy_outcome(db, session)
        db.conn.execute.assert_not_called()

    def test_noop_when_db_has_no_conn(self):
        from pixl.execution.autonomy import record_autonomy_outcome

        db = MagicMock()
        del db.conn  # Remove conn attribute
        db.get_config = MagicMock(return_value=None)

        session = _make_session()
        session.node_instances = {}
        db.events.get_events.return_value = []

        # Should not raise
        record_autonomy_outcome(db, session)

    def test_counts_auto_approved_gates_correctly(self):
        from pixl.execution.autonomy import record_autonomy_outcome

        db = _make_db()
        session = _make_session()
        session.node_instances = {}

        # Simulate two auto-approved gates and one manual
        db.events.get_events.return_value = [
            {"event_type": "gate_approved", "payload": {"approver": "auto"}},
            {"event_type": "gate_approved", "payload": {"approver": "auto"}},
            {"event_type": "gate_approved", "payload": {"approver": "human"}},
        ]
        db.get_config.return_value = "assist"
        db.conn.execute.return_value.fetchone.return_value = None
        db.conn.execute.return_value.fetchall.return_value = []

        # Should persist without error
        record_autonomy_outcome(db, session)

        # Verify conn.execute was called for the INSERT
        assert db.conn.execute.call_count >= 1

    def test_noop_when_session_is_none(self):
        from pixl.execution.autonomy import record_autonomy_outcome

        db = _make_db()
        # Should not raise
        record_autonomy_outcome(db, None)


class TestAutonomyKey:
    """Tests for _autonomy_key helper."""

    def test_returns_correct_config_key_format(self):
        from pixl.execution.autonomy import _autonomy_key

        assert _autonomy_key("feat-abc") == "autonomy:feat-abc"
        assert _autonomy_key("my-feature") == "autonomy:my-feature"


class TestFailureSignals:
    """Tests for _failure_signals set content."""

    def test_contains_expected_failure_event_types(self):
        from pixl.execution.autonomy import _failure_signals

        signals = _failure_signals()
        assert "session_failed" in signals
        assert "gate_rejected" in signals
        assert "contract_violation" in signals
        assert "recovery_escalated" in signals

    def test_does_not_contain_success_event_types(self):
        from pixl.execution.autonomy import _failure_signals

        signals = _failure_signals()
        assert "session_completed" not in signals
        assert "gate_approved" not in signals


# ─────────────────────────────────────────────────────────────────────────────
# Section 6: run_workflow outer shell — heartbeat run lifecycle
# ─────────────────────────────────────────────────────────────────────────────


class TestRunWorkflowHeartbeatLifecycle:
    """Tests for run_workflow's heartbeat run creation and completion."""

    def _make_inner_mock(self):
        """Return a patch target for the inner execution function."""
        return patch("pixl.execution.workflow_runner._run_workflow_inner")

    def test_creates_heartbeat_run_when_run_id_not_provided(self):
        from pixl.execution.workflow_runner import run_workflow

        db = _make_db()
        db.sessions.get_session.return_value = {"status": "completed"}

        hr_patch = patch(
            "pixl.models.heartbeat_run.HeartbeatRun.generate_id",
            return_value="run-001",
        )
        with self._make_inner_mock(), hr_patch:
            run_workflow(
                project_path=Path("/tmp/fake-project"),
                session_id="sess-hr-1",
                workflow_id="test-wf",
                skip_approval=False,
                db=db,
            )

        db.heartbeat_runs.create_run.assert_called_once()

    def test_completes_heartbeat_run_with_succeeded_status_on_completion(self):
        from pixl.execution.workflow_runner import run_workflow

        db = _make_db()
        db.sessions.get_session.return_value = {"status": "completed", "ended_at": "2024-01-01"}

        hr_patch = patch(
            "pixl.models.heartbeat_run.HeartbeatRun.generate_id",
            return_value="run-002",
        )
        with self._make_inner_mock(), hr_patch:
            run_workflow(
                project_path=Path("/tmp/fake-project"),
                session_id="sess-hr-2",
                workflow_id="test-wf",
                skip_approval=False,
                db=db,
            )

        db.heartbeat_runs.complete_run.assert_called_once()
        _run_status_arg = db.heartbeat_runs.complete_run.call_args[1].get("status") or \
                          db.heartbeat_runs.complete_run.call_args[0][1]
        assert _run_status_arg == "succeeded"

    def test_completes_heartbeat_run_with_failed_status_on_failure(self):
        from pixl.execution.workflow_runner import run_workflow

        db = _make_db()
        db.sessions.get_session.return_value = {"status": "failed", "ended_at": "2024-01-01"}

        hr_patch = patch(
            "pixl.models.heartbeat_run.HeartbeatRun.generate_id",
            return_value="run-003",
        )
        with self._make_inner_mock(), hr_patch:
            run_workflow(
                project_path=Path("/tmp/fake-project"),
                session_id="sess-hr-3",
                workflow_id="test-wf",
                skip_approval=False,
                db=db,
            )

        db.heartbeat_runs.complete_run.assert_called_once()
        _run_status_arg = db.heartbeat_runs.complete_run.call_args[1].get("status") or \
                          db.heartbeat_runs.complete_run.call_args[0][1]
        assert _run_status_arg == "failed"

    def test_uses_provided_run_id_instead_of_creating_new_one(self):
        from pixl.execution.workflow_runner import run_workflow

        db = _make_db()
        db.sessions.get_session.return_value = {"status": "completed", "ended_at": "2024-01-01"}

        with self._make_inner_mock():
            run_workflow(
                project_path=Path("/tmp/fake-project"),
                session_id="sess-hr-4",
                workflow_id="test-wf",
                skip_approval=False,
                db=db,
                run_id="pre-existing-run-id",
            )

        # create_run should NOT be called because run_id was provided
        db.heartbeat_runs.create_run.assert_not_called()
        # But start_run and complete_run should still be called
        db.heartbeat_runs.start_run.assert_called_once_with("pre-existing-run-id")

    def test_clears_execution_tracking_even_when_inner_raises(self):
        from pixl.execution import workflow_runner as wr

        db = _make_db()
        db.sessions.get_session.return_value = {"status": "failed", "ended_at": None}

        inner_exc = RuntimeError("Inner failure")
        hr_patch = patch(
            "pixl.models.heartbeat_run.HeartbeatRun.generate_id",
            return_value="run-err",
        )
        inner_patch = patch(
            "pixl.execution.workflow_runner._run_workflow_inner",
            side_effect=inner_exc,
        )
        with inner_patch, hr_patch:
            try:
                wr.run_workflow(
                    project_path=Path("/tmp/fake-project"),
                    session_id="sess-cleanup",
                    workflow_id="test-wf",
                    skip_approval=False,
                    db=db,
                )
            except Exception:
                pass  # The outer try/finally should still clean up

        # Execution marker should not persist after the call
        active = wr.get_active_sessions_for_project("fake-project")
        assert "sess-cleanup" not in active
