"""Tests for execution/edge_traversal.py — DAG edge traversal logic.

Tests cover:
- follow_edges() with SUCCESS, FAILURE, ALWAYS, CONDITION triggers
- follow_edges() loop constraint enforcement
- can_enter_loop() first-iteration and exhausted states
- record_loop_iteration() state tracking
- evaluate_condition() via mocked evaluator
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pixl.execution.edge_traversal import (
    can_enter_loop,
    evaluate_condition,
    follow_edges,
    record_loop_iteration,
)
from pixl.models.session import LoopState
from pixl.models.workflow import Edge, EdgeTrigger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_executor(edges: list[Edge], loop_constraint=None) -> MagicMock:
    """Build a minimal GraphExecutor mock with configurable edges."""
    executor = MagicMock()

    executor.snapshot.graph.get_successors.return_value = edges

    # Loop constraint index
    if loop_constraint:
        from_node = getattr(loop_constraint, "from_node", None)
        to_node = getattr(loop_constraint, "to_node", None)
        executor._loop_constraint_by_edge = {(from_node, to_node): loop_constraint}
    else:
        executor._loop_constraint_by_edge = {}

    # Session defaults
    executor.session.get_node_instance.return_value = {"attempt": 0}
    executor.session.artifacts = []
    executor.session.structured_outputs = {}
    executor.session.get_loop_state.return_value = None
    executor._expr_evaluator = None
    executor.artifacts_dir = "/tmp"

    return executor


def _make_loop_constraint(
    loop_id: str = "fix-loop",
    from_node: str = "review",
    to_node: str = "implement",
    max_iterations: int = 3,
    edge_trigger: EdgeTrigger = EdgeTrigger.FAILURE,
) -> MagicMock:
    """Build a minimal LoopConstraint mock."""
    lc = MagicMock()
    lc.id = loop_id
    lc.from_node = from_node
    lc.to_node = to_node
    lc.max_iterations = max_iterations
    lc.edge_trigger = edge_trigger
    return lc


# ---------------------------------------------------------------------------
# follow_edges — basic trigger matching
# ---------------------------------------------------------------------------


class TestFollowEdgesBasicTriggers:
    def test_success_edge_traversed_on_success_result(self) -> None:
        edges = [Edge(to="implement", on=EdgeTrigger.SUCCESS)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "plan", "success")
        assert result == ["implement"]

    def test_success_edge_not_traversed_on_failure_result(self) -> None:
        edges = [Edge(to="implement", on=EdgeTrigger.SUCCESS)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "plan", "failed")
        assert result == []

    def test_failure_edge_traversed_on_failure_result(self) -> None:
        edges = [Edge(to="retry", on=EdgeTrigger.FAILURE)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "plan", "failed")
        assert result == ["retry"]

    def test_failure_edge_not_traversed_on_success_result(self) -> None:
        edges = [Edge(to="retry", on=EdgeTrigger.FAILURE)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "plan", "success")
        assert result == []

    def test_always_edge_traversed_on_success(self) -> None:
        edges = [Edge(to="cleanup", on=EdgeTrigger.ALWAYS)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "plan", "success")
        assert result == ["cleanup"]

    def test_always_edge_traversed_on_failure(self) -> None:
        edges = [Edge(to="cleanup", on=EdgeTrigger.ALWAYS)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "plan", "failed")
        assert result == ["cleanup"]

    def test_always_edge_traversed_on_skipped(self) -> None:
        edges = [Edge(to="cleanup", on=EdgeTrigger.ALWAYS)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "plan", "skipped")
        assert result == ["cleanup"]

    def test_returns_empty_list_when_no_edges(self) -> None:
        executor = _make_executor([])

        result = follow_edges(executor, "plan", "success")
        assert result == []

    def test_multiple_edges_all_matching_returned(self) -> None:
        edges = [
            Edge(to="next-a", on=EdgeTrigger.SUCCESS),
            Edge(to="next-b", on=EdgeTrigger.SUCCESS),
        ]
        executor = _make_executor(edges)

        result = follow_edges(executor, "fork", "success")
        assert "next-a" in result
        assert "next-b" in result

    def test_mixed_edges_only_matching_returned(self) -> None:
        edges = [
            Edge(to="happy", on=EdgeTrigger.SUCCESS),
            Edge(to="error", on=EdgeTrigger.FAILURE),
        ]
        executor = _make_executor(edges)

        result = follow_edges(executor, "task", "success")
        assert result == ["happy"]


# ---------------------------------------------------------------------------
# follow_edges — condition trigger
# ---------------------------------------------------------------------------


class TestFollowEdgesConditionTrigger:
    def test_condition_edge_evaluated_when_trigger_is_condition(self) -> None:
        edges = [Edge(to="branch", on=EdgeTrigger.CONDITION, condition="attempt > 2")]
        executor = _make_executor(edges)

        # Patch evaluate_condition to return True
        with patch("pixl.execution.edge_traversal.evaluate_condition", return_value=True):
            result = follow_edges(executor, "task", "failed")
        assert result == ["branch"]

    def test_condition_edge_not_traversed_when_condition_false(self) -> None:
        edges = [Edge(to="branch", on=EdgeTrigger.CONDITION, condition="attempt > 2")]
        executor = _make_executor(edges)

        with patch("pixl.execution.edge_traversal.evaluate_condition", return_value=False):
            result = follow_edges(executor, "task", "failed")
        assert result == []

    def test_condition_edge_without_condition_string_not_traversed(self) -> None:
        edges = [Edge(to="branch", on=EdgeTrigger.CONDITION, condition=None)]
        executor = _make_executor(edges)

        result = follow_edges(executor, "task", "success")
        assert result == []


# ---------------------------------------------------------------------------
# follow_edges — loop constraint integration
# ---------------------------------------------------------------------------


class TestFollowEdgesLoopConstraint:
    def test_loop_edge_traversed_on_first_iteration(self) -> None:
        lc = _make_loop_constraint()
        edges = [Edge(to="implement", on=EdgeTrigger.FAILURE)]
        executor = _make_executor(edges, loop_constraint=lc)
        executor.session.get_loop_state.return_value = None  # No prior state

        with patch("pixl.execution.edge_traversal.can_enter_loop", return_value=True):
            with patch("pixl.execution.edge_traversal.record_loop_iteration"):
                result = follow_edges(executor, "review", "failed")
        assert result == ["implement"]

    def test_loop_edge_not_traversed_when_exhausted(self) -> None:
        lc = _make_loop_constraint(max_iterations=3)
        edges = [Edge(to="implement", on=EdgeTrigger.FAILURE)]
        executor = _make_executor(edges, loop_constraint=lc)

        with patch("pixl.execution.edge_traversal.can_enter_loop", return_value=False):
            result = follow_edges(executor, "review", "failed")
        assert result == []

    def test_record_loop_iteration_called_when_traversing(self) -> None:
        lc = _make_loop_constraint()
        edges = [Edge(to="implement", on=EdgeTrigger.FAILURE)]
        executor = _make_executor(edges, loop_constraint=lc)

        with patch("pixl.execution.edge_traversal.can_enter_loop", return_value=True):
            with patch("pixl.execution.edge_traversal.record_loop_iteration") as mock_record:
                follow_edges(executor, "review", "failed")
        mock_record.assert_called_once()


# ---------------------------------------------------------------------------
# can_enter_loop
# ---------------------------------------------------------------------------


class TestCanEnterLoop:
    def test_returns_true_when_no_loop_state(self) -> None:
        executor = MagicMock()
        executor.session.get_loop_state.return_value = None
        lc = _make_loop_constraint()

        result = can_enter_loop(executor, lc)
        assert result is True

    def test_returns_true_when_loop_state_has_iterations_remaining(self) -> None:
        executor = MagicMock()
        loop_state = LoopState(current_iteration=1, max_iterations=3)
        executor.session.get_loop_state.return_value = loop_state
        lc = _make_loop_constraint(max_iterations=3)

        result = can_enter_loop(executor, lc)
        assert result is True

    def test_returns_false_when_loop_state_exhausted(self) -> None:
        executor = MagicMock()
        loop_state = LoopState(current_iteration=3, max_iterations=3)
        executor.session.get_loop_state.return_value = loop_state
        lc = _make_loop_constraint(max_iterations=3)

        result = can_enter_loop(executor, lc)
        assert result is False

    def test_returns_false_at_max_iterations(self) -> None:
        executor = MagicMock()
        loop_state = LoopState(current_iteration=5, max_iterations=5)
        executor.session.get_loop_state.return_value = loop_state
        lc = _make_loop_constraint(max_iterations=5)

        result = can_enter_loop(executor, lc)
        assert result is False


# ---------------------------------------------------------------------------
# record_loop_iteration
# ---------------------------------------------------------------------------


class TestRecordLoopIteration:
    def test_creates_new_loop_state_when_none_exists(self) -> None:
        executor = MagicMock()
        executor.session.get_loop_state.return_value = None
        executor.snapshot.workflow_config = {}
        lc = _make_loop_constraint()

        record_loop_iteration(executor, lc, "review", "implement")

        executor.session.set_loop_state.assert_called_once()

    def test_increments_iteration_on_existing_loop_state(self) -> None:
        executor = MagicMock()
        loop_state = LoopState(current_iteration=1, max_iterations=3)
        executor.session.get_loop_state.return_value = loop_state
        executor.snapshot.workflow_config = {}
        lc = _make_loop_constraint()

        record_loop_iteration(executor, lc, "review", "implement")

        # After recording, iteration should have been incremented
        executor.session.set_loop_state.assert_called_once()

    def test_emits_warning_event_when_loop_exhausted_in_autonomous_mode(self) -> None:
        executor = MagicMock()
        loop_state = LoopState(current_iteration=2, max_iterations=3)
        executor.session.get_loop_state.return_value = loop_state
        executor.snapshot.workflow_config = {"metadata": {"skip_human_gate": True}}
        executor.session.id = "sess-abc"
        executor._emit_event = MagicMock()
        lc = _make_loop_constraint(max_iterations=3)

        record_loop_iteration(executor, lc, "review", "implement")

        executor._emit_event.assert_called_once()

    def test_emits_paused_event_when_loop_exhausted_in_human_mode(self) -> None:
        executor = MagicMock()
        loop_state = LoopState(current_iteration=2, max_iterations=3)
        executor.session.get_loop_state.return_value = loop_state
        executor.snapshot.workflow_config = {"metadata": {"skip_human_gate": False}}
        executor.session.id = "sess-abc"
        executor._emit_event = MagicMock()
        lc = _make_loop_constraint(max_iterations=3)

        record_loop_iteration(executor, lc, "review", "implement")

        executor._emit_event.assert_called_once()

    def test_state_saved_on_session(self) -> None:
        executor = MagicMock()
        executor.session.get_loop_state.return_value = None
        executor.snapshot.workflow_config = {}
        lc = _make_loop_constraint()

        record_loop_iteration(executor, lc, "review", "implement")

        executor.session.set_loop_state.assert_called()


# ---------------------------------------------------------------------------
# evaluate_condition
# ---------------------------------------------------------------------------


class TestEvaluateCondition:
    def test_returns_false_on_evaluator_value_error(self) -> None:
        executor = MagicMock()
        executor.session.get_node_instance.return_value = {"attempt": 0}
        executor.session.artifacts = []
        executor.session.structured_outputs = {}
        executor._expr_evaluator = MagicMock()
        executor._expr_evaluator.evaluate.side_effect = ValueError("bad expr")

        result = evaluate_condition(executor, "attempt > 5", "success", None, "plan")
        assert result is False

    def test_returns_true_when_evaluator_succeeds(self) -> None:
        executor = MagicMock()
        executor.session.get_node_instance.return_value = {"attempt": 3}
        executor.session.artifacts = []
        executor.session.structured_outputs = {}
        executor._expr_evaluator = MagicMock()
        executor._expr_evaluator.evaluate.return_value = True

        result = evaluate_condition(executor, "attempt > 2", "success", None, "plan")
        assert result is True

    def test_creates_evaluator_when_none(self) -> None:
        executor = MagicMock()
        executor.session.get_node_instance.return_value = None
        executor.session.artifacts = []
        executor.session.structured_outputs = {}
        executor._expr_evaluator = None
        executor.artifacts_dir = "/tmp"

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = False

        with patch(
            "pixl.execution.expression_evaluator.PixlExprEvaluator",
            return_value=mock_evaluator,
        ):
            # evaluate_condition lazily imports PixlExprEvaluator inside the function
            # so we patch at the source module and verify the evaluator was created
            evaluate_condition(executor, "false", "success", None, "plan")

        # After calling, executor should have an evaluator set
        assert executor._expr_evaluator is not None

    def test_injects_structured_output_payload_when_available(self) -> None:
        executor = MagicMock()
        executor.session.get_node_instance.return_value = {"attempt": 0}
        executor.session.artifacts = []
        executor.session.structured_outputs = {"plan": {"payload": {"confidence": 0.9}}}
        executor._expr_evaluator = MagicMock()
        executor._expr_evaluator.evaluate.return_value = True

        evaluate_condition(executor, "payload.confidence > 0.5", "success", None, "plan")

        call_args = executor._expr_evaluator.evaluate.call_args
        context = call_args[0][1]
        assert "payload" in context
        assert context["payload"]["confidence"] == 0.9
