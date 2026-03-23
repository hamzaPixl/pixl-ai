"""Tests for execute_simulated() stub output generation."""

from unittest.mock import MagicMock

from pixl.execution.task_executor import execute_simulated
from pixl.models.event import EventType
from pixl.models.node_instance import NodeState


def _make_node(node_id: str = "plan", task_config: MagicMock | None = None) -> MagicMock:
    """Create a minimal mock Node."""
    node = MagicMock()
    node.id = node_id
    node.task_config = task_config
    return node


class TestExecuteSimulated:
    def test_returns_success(self) -> None:
        node = _make_node()
        result = execute_simulated(node, {})

        assert result["success"] is True
        assert result["state"] == NodeState.TASK_COMPLETED
        assert result["result_state"] == "success"
        assert result["final_event_type"] == EventType.TASK_COMPLETED

    def test_payload_has_simulated_flag(self) -> None:
        node = _make_node()
        result = execute_simulated(node, {})

        assert result["final_event_payload"]["simulated"] is True

    def test_stub_output_contains_node_id(self) -> None:
        node = _make_node(node_id="generate-plan")
        result = execute_simulated(node, {})

        output = result["final_event_payload"]["output"]
        assert "generate-plan" in output
        assert "[SIMULATED]" in output

    def test_stub_output_with_output_artifact(self) -> None:
        task_config = MagicMock()
        task_config.output_artifact = "plan.md"
        node = _make_node(node_id="plan", task_config=task_config)

        result = execute_simulated(node, {})

        output = result["final_event_payload"]["output"]
        assert "plan.md" in output
        assert "[SIMULATED]" in output

    def test_stub_output_without_output_artifact(self) -> None:
        task_config = MagicMock(spec=[])  # no output_artifact attribute
        node = _make_node(node_id="build", task_config=task_config)

        result = execute_simulated(node, {})

        output = result["final_event_payload"]["output"]
        assert "build" in output

    def test_events_list_empty(self) -> None:
        node = _make_node()
        result = execute_simulated(node, {})

        assert result["events"] == []
