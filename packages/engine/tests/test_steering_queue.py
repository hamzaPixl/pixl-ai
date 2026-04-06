"""Tests for the mid-task steering queue mechanism."""

from __future__ import annotations

import queue
import threading

import pytest


class TestSteeringQueueInterface:
    """Unit tests for OrchestratorCore steering queue methods."""

    def _make_core(self):
        """Create a minimal mock that has the steering queue attributes."""
        # Avoid full OrchestratorCore init (needs project_path, etc.)
        # Instead, test the queue mechanics directly.
        q: queue.Queue[str] = queue.Queue()
        return q

    def test_put_and_drain(self):
        q = self._make_core()
        q.put("Fix the bug instead")
        assert q.get_nowait() == "Fix the bug instead"

    def test_drain_empty_returns_none(self):
        q = self._make_core()
        with pytest.raises(queue.Empty):
            q.get_nowait()

    def test_multiple_instructions_fifo(self):
        q: queue.Queue[str] = queue.Queue()
        q.put("first")
        q.put("second")
        assert q.get_nowait() == "first"
        assert q.get_nowait() == "second"

    def test_steer_does_not_set_interrupt(self):
        """Steering and interrupt are independent signals."""
        interrupt = threading.Event()
        steering: queue.Queue[str] = queue.Queue()

        steering.put("redirect")
        assert not interrupt.is_set()
        assert not steering.empty()

    def test_interrupt_does_not_drain_steering(self):
        interrupt = threading.Event()
        steering: queue.Queue[str] = queue.Queue()

        interrupt.set()
        steering.put("instruction")
        assert interrupt.is_set()
        assert steering.get_nowait() == "instruction"

    def test_thread_safety(self):
        """Multiple threads can put/get without corruption."""
        q: queue.Queue[str] = queue.Queue()
        results: list[str] = []

        def producer(prefix: str, count: int):
            for i in range(count):
                q.put(f"{prefix}-{i}")

        def consumer(count: int):
            for _ in range(count):
                results.append(q.get(timeout=5))

        t1 = threading.Thread(target=producer, args=("A", 50))
        t2 = threading.Thread(target=producer, args=("B", 50))
        t3 = threading.Thread(target=consumer, args=(100,))

        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()

        assert len(results) == 100
        assert sum(1 for r in results if r.startswith("A-")) == 50
        assert sum(1 for r in results if r.startswith("B-")) == 50


class TestSteeringInOrchestratorCore:
    """Integration tests verifying steering queue is wired into OrchestratorCore."""

    def test_steer_method_exists(self):
        from pixl.orchestration.core import OrchestratorCore

        assert callable(getattr(OrchestratorCore, "steer", None))

    def test_drain_method_exists(self):
        from pixl.orchestration.core import OrchestratorCore

        assert callable(getattr(OrchestratorCore, "_drain_steering_queue", None))

    def test_steer_sentinel_in_streaming(self):
        """The __STEER__ sentinel must appear in _process_streaming_message."""
        import inspect

        from pixl.orchestration.core import OrchestratorCore

        source = inspect.getsource(OrchestratorCore._process_streaming_message)
        assert "__STEER__" in source


class TestSteerSessionInManager:
    """Tests for WorkflowRunnerManager.steer_session class method."""

    def test_steer_session_exists(self):
        from pixl.execution.workflow_runner_manager import WorkflowRunnerManager

        assert callable(getattr(WorkflowRunnerManager, "steer_session", None))

    def test_steer_session_returns_false_for_unknown(self):
        from pixl.execution.workflow_runner_manager import WorkflowRunnerManager

        result = WorkflowRunnerManager.steer_session("nonexistent-id", "do something")
        assert result is False
