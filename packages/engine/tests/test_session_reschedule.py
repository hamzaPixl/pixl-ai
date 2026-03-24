"""Tests for WorkflowSession.reschedule_node()."""

import logging

from pixl.models.session import ExecutorCursor, WorkflowSession


def _make_session(**kwargs) -> WorkflowSession:
    """Create a minimal WorkflowSession for testing."""
    defaults = {
        "id": "sess-test0001",
        "feature_id": "feat-001",
        "snapshot_hash": "abc123",
    }
    defaults.update(kwargs)
    return WorkflowSession(**defaults)


class TestRescheduleNode:
    """Tests for WorkflowSession.reschedule_node."""

    def test_removes_completed_node_and_adds_successors(self):
        """Should remove the completed node from ready queue and add successors."""
        cursor = ExecutorCursor(
            current_node_id="node-a",
            ready_queue=["node-a", "node-b"],
        )
        session = _make_session(executor_cursor=cursor)

        session.reschedule_node("node-a", ["node-c", "node-d"])

        assert session.executor_cursor is not None
        assert session.executor_cursor.current_node_id is None
        assert "node-a" not in session.executor_cursor.ready_queue
        assert "node-c" in session.executor_cursor.ready_queue
        assert "node-d" in session.executor_cursor.ready_queue
        # node-b should still be present
        assert "node-b" in session.executor_cursor.ready_queue

    def test_ready_queue_is_sorted_after_reschedule(self):
        """Ready queue should maintain sorted order after rescheduling."""
        cursor = ExecutorCursor(
            current_node_id="node-b",
            ready_queue=["node-a", "node-b"],
        )
        session = _make_session(executor_cursor=cursor)

        session.reschedule_node("node-b", ["node-z", "node-c"])

        assert session.executor_cursor is not None
        queue = session.executor_cursor.ready_queue
        assert queue == sorted(queue)

    def test_no_op_when_cursor_is_none(self, caplog):
        """Should log a warning and return when executor_cursor is None."""
        session = _make_session(executor_cursor=None)

        with caplog.at_level(logging.WARNING):
            session.reschedule_node("node-a", ["node-b"])

        assert "no executor cursor" in caplog.text.lower()

    def test_empty_successor_list(self):
        """Should handle an empty successor list (terminal node)."""
        cursor = ExecutorCursor(
            current_node_id="node-a",
            ready_queue=["node-a"],
        )
        session = _make_session(executor_cursor=cursor)

        session.reschedule_node("node-a", [])

        assert session.executor_cursor is not None
        assert session.executor_cursor.current_node_id is None
        assert session.executor_cursor.ready_queue == []

    def test_does_not_duplicate_existing_ready_nodes(self):
        """Should not add a successor that is already in the ready queue."""
        cursor = ExecutorCursor(
            current_node_id="node-a",
            ready_queue=["node-a", "node-b"],
        )
        session = _make_session(executor_cursor=cursor)

        session.reschedule_node("node-a", ["node-b", "node-c"])

        assert session.executor_cursor is not None
        # node-b should appear exactly once
        assert session.executor_cursor.ready_queue.count("node-b") == 1
        assert "node-c" in session.executor_cursor.ready_queue
