"""Tests for execution/node_state.py — node instance lifecycle management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pixl.execution.node_state import (
    allow_simulated_execution,
    get_or_create_node_instance,
    reset_instance_to_pending,
    resolve_agent_and_model,
    update_node_instance_metadata,
    update_node_instance_state,
    workflow_max_attempts,
)
from pixl.models.node_instance import NodeState
from pixl.models.session import WorkflowSession, create_node_instance

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> WorkflowSession:
    """Build a minimal WorkflowSession with empty node state."""
    session = MagicMock(spec=WorkflowSession)
    session.id = "sess-test-001"
    session._node_instances: dict = {}

    def _get_node(node_id: str):
        return session._node_instances.get(node_id)

    def _set_node(node_id: str, instance: dict):
        session._node_instances[node_id] = instance

    def _update_state(node_id: str, state: str):
        if node_id in session._node_instances:
            session._node_instances[node_id]["state"] = state

    session.get_node_instance = _get_node
    session.set_node_instance = _set_node
    session.update_node_state = _update_state
    return session


def _make_node(
    agent: str = "backend-engineer", model: str | None = "claude-sonnet-4-6"
) -> MagicMock:
    node = MagicMock()
    node.task_config = MagicMock()
    node.task_config.agent = agent
    node.task_config.model = model
    return node


# ---------------------------------------------------------------------------
# update_node_instance_state
# ---------------------------------------------------------------------------


class TestUpdateNodeInstanceState:
    def test_creates_instance_if_missing_and_sets_state(self) -> None:
        session = _make_session()
        update_node_instance_state(session, "plan", NodeState.TASK_RUNNING, {})
        inst = session.get_node_instance("plan")
        assert inst is not None
        assert inst["state"] == NodeState.TASK_RUNNING.value

    def test_sets_started_at_when_running(self) -> None:
        session = _make_session()
        update_node_instance_state(session, "plan", NodeState.TASK_RUNNING, {})
        inst = session.get_node_instance("plan")
        assert inst["started_at"] is not None

    def test_sets_ended_at_for_terminal_state(self) -> None:
        session = _make_session()
        update_node_instance_state(session, "plan", NodeState.TASK_COMPLETED, {})
        inst = session.get_node_instance("plan")
        assert inst["ended_at"] is not None

    def test_does_not_set_ended_at_for_running_state(self) -> None:
        session = _make_session()
        update_node_instance_state(session, "plan", NodeState.TASK_RUNNING, {})
        inst = session.get_node_instance("plan")
        assert inst.get("ended_at") is None

    def test_sets_failure_kind_on_failure(self) -> None:
        session = _make_session()
        update_node_instance_state(
            session,
            "plan",
            NodeState.TASK_FAILED,
            {"failure_kind": "transient", "error": "timeout"},
        )
        inst = session.get_node_instance("plan")
        assert inst["failure_kind"] == "transient"

    def test_sets_error_message_on_failure(self) -> None:
        session = _make_session()
        update_node_instance_state(
            session, "plan", NodeState.TASK_FAILED, {"failure_kind": "fatal", "error": "oom"}
        )
        inst = session.get_node_instance("plan")
        assert inst["error_message"] == "oom"

    def test_updates_existing_instance(self) -> None:
        session = _make_session()
        # Create first
        update_node_instance_state(session, "plan", NodeState.TASK_RUNNING, {})
        # Then transition
        update_node_instance_state(session, "plan", NodeState.TASK_COMPLETED, {})
        inst = session.get_node_instance("plan")
        assert inst["state"] == NodeState.TASK_COMPLETED.value


# ---------------------------------------------------------------------------
# update_node_instance_metadata
# ---------------------------------------------------------------------------


class TestUpdateNodeInstanceMetadata:
    def test_creates_instance_if_missing(self) -> None:
        session = _make_session()
        update_node_instance_metadata(session, "build", agent_name="qa-engineer")
        inst = session.get_node_instance("build")
        assert inst is not None

    def test_sets_agent_name(self) -> None:
        session = _make_session()
        update_node_instance_metadata(session, "build", agent_name="qa-engineer")
        inst = session.get_node_instance("build")
        assert inst["agent_name"] == "qa-engineer"

    def test_sets_model_name(self) -> None:
        session = _make_session()
        update_node_instance_metadata(session, "build", model_name="claude-haiku-4-5")
        inst = session.get_node_instance("build")
        assert inst["model_name"] == "claude-haiku-4-5"

    def test_sets_max_attempts(self) -> None:
        session = _make_session()
        update_node_instance_metadata(session, "build", max_attempts=5)
        inst = session.get_node_instance("build")
        assert inst["max_attempts"] == 5

    def test_sets_llm_session_id(self) -> None:
        session = _make_session()
        update_node_instance_metadata(session, "build", llm_session_id="sess-xyz-001")
        inst = session.get_node_instance("build")
        assert inst["llm_session_id"] == "sess-xyz-001"

    def test_sets_provider_session_id(self) -> None:
        session = _make_session()
        update_node_instance_metadata(session, "build", provider_session_id="gemini-abc")
        inst = session.get_node_instance("build")
        assert inst["provider_session_id"] == "gemini-abc"

    def test_does_not_overwrite_with_none(self) -> None:
        session = _make_session()
        update_node_instance_metadata(session, "build", agent_name="architect")
        # Call again with None — should not overwrite
        update_node_instance_metadata(session, "build", agent_name=None)
        inst = session.get_node_instance("build")
        assert inst["agent_name"] == "architect"

    def test_updates_existing_instance_in_place(self) -> None:
        session = _make_session()
        # First call sets agent
        update_node_instance_metadata(session, "build", agent_name="arch")
        # Second call adds model
        update_node_instance_metadata(session, "build", model_name="claude-opus-4-6")
        inst = session.get_node_instance("build")
        assert inst["agent_name"] == "arch"
        assert inst["model_name"] == "claude-opus-4-6"


# ---------------------------------------------------------------------------
# get_or_create_node_instance
# ---------------------------------------------------------------------------


class TestGetOrCreateNodeInstance:
    def test_returns_existing_instance(self) -> None:
        session = _make_session()
        existing = create_node_instance("plan", "task_running")
        session.set_node_instance("plan", existing)

        result = get_or_create_node_instance(session, "plan")
        assert result is existing

    def test_creates_new_instance_when_missing(self) -> None:
        session = _make_session()
        result = get_or_create_node_instance(session, "plan")
        assert result is not None
        assert result["node_id"] == "plan"

    def test_new_instance_has_correct_node_id(self) -> None:
        session = _make_session()
        result = get_or_create_node_instance(session, "verify-step")
        assert result["node_id"] == "verify-step"


# ---------------------------------------------------------------------------
# reset_instance_to_pending
# ---------------------------------------------------------------------------


class TestResetInstanceToPending:
    def test_does_nothing_when_instance_missing(self) -> None:
        session = _make_session()
        # Should not raise
        reset_instance_to_pending(session, "nonexistent-node")

    def test_sets_state_to_task_pending(self) -> None:
        session = _make_session()
        inst = create_node_instance("build", "task_running")
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build")
        result = session.get_node_instance("build")
        assert result["state"] == NodeState.TASK_PENDING.value

    def test_clears_started_at(self) -> None:
        session = _make_session()
        inst = create_node_instance("build", "task_running")
        inst["started_at"] = "2024-01-01T00:00:00"
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build")
        result = session.get_node_instance("build")
        assert result["started_at"] is None

    def test_clears_ended_at(self) -> None:
        session = _make_session()
        inst = create_node_instance("build", "task_completed")
        inst["ended_at"] = "2024-01-01T01:00:00"
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build")
        result = session.get_node_instance("build")
        assert result["ended_at"] is None

    def test_increments_attempt_by_default(self) -> None:
        session = _make_session()
        inst = create_node_instance("build")
        inst["attempt"] = 2
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build")
        result = session.get_node_instance("build")
        assert result["attempt"] == 3

    def test_does_not_increment_attempt_when_disabled(self) -> None:
        session = _make_session()
        inst = create_node_instance("build")
        inst["attempt"] = 2
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build", increment_attempt=False)
        result = session.get_node_instance("build")
        assert result["attempt"] == 2

    def test_clears_error_fields_when_requested(self) -> None:
        session = _make_session()
        inst = create_node_instance("build", "task_failed")
        inst["failure_kind"] = "transient"
        inst["error_message"] = "timeout"
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build", clear_error_fields=True)
        result = session.get_node_instance("build")
        assert result["failure_kind"] is None
        assert result["error_message"] is None

    def test_clears_blocked_reason_when_requested(self) -> None:
        session = _make_session()
        inst = create_node_instance("build", "task_blocked")
        inst["blocked_reason"] = "waiting for input"
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build", clear_blocked_reason=True)
        result = session.get_node_instance("build")
        assert result["blocked_reason"] is None

    def test_sets_resume_session_id_when_provided(self) -> None:
        session = _make_session()
        inst = create_node_instance("build", "task_running")
        session.set_node_instance("build", inst)

        reset_instance_to_pending(session, "build", resume_session_id="sess-resume-abc")
        result = session.get_node_instance("build")
        assert result["resume_session_id"] == "sess-resume-abc"


# ---------------------------------------------------------------------------
# resolve_agent_and_model
# ---------------------------------------------------------------------------


class TestResolveAgentAndModel:
    def test_returns_none_none_when_no_task_config(self) -> None:
        node = MagicMock()
        node.task_config = None
        agent, model = resolve_agent_and_model(node, MagicMock())
        assert agent is None
        assert model is None

    def test_returns_agent_from_task_config(self) -> None:
        node = _make_node(agent="architect")
        agent, _ = resolve_agent_and_model(node, MagicMock())
        assert agent == "architect"

    def test_returns_model_from_task_config(self) -> None:
        node = _make_node(model="claude-opus-4-6")
        _, model = resolve_agent_and_model(node, MagicMock())
        assert model == "claude-opus-4-6"

    def test_defaults_model_to_sonnet_when_none(self) -> None:
        node = _make_node(model=None)
        _, model = resolve_agent_and_model(node, MagicMock())
        assert model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# workflow_max_attempts
# ---------------------------------------------------------------------------


class TestWorkflowMaxAttempts:
    def _make_snapshot(self, workflow_config: dict) -> MagicMock:
        snapshot = MagicMock()
        snapshot.workflow_config = workflow_config
        return snapshot

    def test_defaults_to_3_when_no_config(self) -> None:
        snapshot = self._make_snapshot({})
        assert workflow_max_attempts(snapshot) == 3

    def test_reads_max_attempts_from_config(self) -> None:
        snapshot = self._make_snapshot({"max_attempts": 7})
        assert workflow_max_attempts(snapshot) == 7

    def test_reads_from_confidence_block(self) -> None:
        snapshot = self._make_snapshot({"confidence": {"max_iterations": 5}})
        assert workflow_max_attempts(snapshot) == 5

    def test_confidence_block_takes_precedence_over_max_attempts(self) -> None:
        snapshot = self._make_snapshot({"max_attempts": 10, "confidence": {"max_iterations": 4}})
        assert workflow_max_attempts(snapshot) == 4

    def test_clamps_to_minimum_of_1(self) -> None:
        snapshot = self._make_snapshot({"max_attempts": 0})
        assert workflow_max_attempts(snapshot) == 1

    def test_clamps_to_maximum_of_20(self) -> None:
        snapshot = self._make_snapshot({"max_attempts": 100})
        assert workflow_max_attempts(snapshot) == 20

    def test_handles_invalid_string_with_default(self) -> None:
        snapshot = self._make_snapshot({"max_attempts": "invalid"})
        assert workflow_max_attempts(snapshot) == 3

    def test_handles_none_config(self) -> None:
        snapshot = self._make_snapshot(None)
        assert workflow_max_attempts(snapshot) == 3

    def test_handles_string_number_in_confidence(self) -> None:
        snapshot = self._make_snapshot({"confidence": {"max_iterations": "6"}})
        assert workflow_max_attempts(snapshot) == 6


# ---------------------------------------------------------------------------
# allow_simulated_execution
# ---------------------------------------------------------------------------


class TestAllowSimulatedExecution:
    def test_returns_true_in_pytest_context(self) -> None:
        # Since we ARE in pytest, PYTEST_CURRENT_TEST is set
        result = allow_simulated_execution()
        assert result is True

    def test_returns_true_when_env_var_is_1(self) -> None:
        with patch.dict(
            "os.environ", {"PYTEST_CURRENT_TEST": "", "PIXL_ALLOW_SIMULATED_EXECUTION": "1"}
        ):
            result = allow_simulated_execution()
            assert result is True

    def test_returns_false_when_env_var_is_false(self) -> None:
        import os

        saved = os.environ.pop("PYTEST_CURRENT_TEST", None)
        try:
            with patch.dict("os.environ", {"PIXL_ALLOW_SIMULATED_EXECUTION": "false"}, clear=False):
                os.environ.pop("PYTEST_CURRENT_TEST", None)
                result = allow_simulated_execution()
                assert result is False
        finally:
            if saved is not None:
                os.environ["PYTEST_CURRENT_TEST"] = saved
