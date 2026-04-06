"""Tests for pixl.utils.task_graph — toposort, cycle detection, critical path."""

from __future__ import annotations

import pytest
from pixl.utils.task_graph import (
    compute_critical_path,
    compute_execution_order,
    validate_task_graph,
)


class TestValidateTaskGraph:
    def test_empty_graph(self):
        result = validate_task_graph([])
        assert result.valid is True
        assert result.errors == []

    def test_acyclic_graph(self):
        tasks = [
            {"id": "A", "blockedBy": []},
            {"id": "B", "blockedBy": ["A"]},
            {"id": "C", "blockedBy": ["A"]},
            {"id": "D", "blockedBy": ["B", "C"]},
        ]
        result = validate_task_graph(tasks)
        assert result.valid is True

    def test_cycle_detected(self):
        tasks = [
            {"id": "A", "blockedBy": ["B"]},
            {"id": "B", "blockedBy": ["A"]},
        ]
        result = validate_task_graph(tasks)
        assert result.valid is False
        assert len(result.cycle_members) > 0
        assert "A" in result.cycle_members or "B" in result.cycle_members

    def test_three_node_cycle(self):
        tasks = [
            {"id": "A", "blockedBy": ["C"]},
            {"id": "B", "blockedBy": ["A"]},
            {"id": "C", "blockedBy": ["B"]},
        ]
        result = validate_task_graph(tasks)
        assert result.valid is False

    def test_orphan_references(self):
        tasks = [
            {"id": "A", "blockedBy": ["GHOST"]},
        ]
        result = validate_task_graph(tasks)
        assert result.valid is False
        assert "A" in result.orphan_refs
        assert "GHOST" in result.orphan_refs["A"]

    def test_self_dependency(self):
        tasks = [
            {"id": "A", "blockedBy": ["A"]},
        ]
        result = validate_task_graph(tasks)
        assert result.valid is False
        assert "A" in result.self_deps

    def test_mixed_errors(self):
        tasks = [
            {"id": "A", "blockedBy": ["A"]},  # self-dep
            {"id": "B", "blockedBy": ["NOPE"]},  # orphan
        ]
        result = validate_task_graph(tasks)
        assert result.valid is False
        assert len(result.errors) >= 2

    def test_no_blockedby_key(self):
        tasks = [{"id": "A"}, {"id": "B"}]
        result = validate_task_graph(tasks)
        assert result.valid is True


class TestComputeExecutionOrder:
    def test_empty(self):
        assert compute_execution_order([]) == []

    def test_linear_chain(self):
        tasks = [
            {"id": "A", "blockedBy": []},
            {"id": "B", "blockedBy": ["A"]},
            {"id": "C", "blockedBy": ["B"]},
        ]
        order = compute_execution_order(tasks)
        assert order.index("A") < order.index("B") < order.index("C")

    def test_parallel_tasks(self):
        tasks = [
            {"id": "A", "blockedBy": []},
            {"id": "B", "blockedBy": []},
            {"id": "C", "blockedBy": ["A", "B"]},
        ]
        order = compute_execution_order(tasks)
        assert order.index("C") > order.index("A")
        assert order.index("C") > order.index("B")

    def test_raises_on_cycle(self):
        tasks = [
            {"id": "A", "blockedBy": ["B"]},
            {"id": "B", "blockedBy": ["A"]},
        ]
        with pytest.raises(ValueError, match="cycle"):
            compute_execution_order(tasks)


class TestComputeCriticalPath:
    def test_empty(self):
        assert compute_critical_path([]) == []

    def test_single_task(self):
        tasks = [{"id": "A", "blockedBy": [], "size": "S"}]
        assert compute_critical_path(tasks) == ["A"]

    def test_linear_chain(self):
        tasks = [
            {"id": "A", "blockedBy": [], "size": "S"},
            {"id": "B", "blockedBy": ["A"], "size": "M"},
            {"id": "C", "blockedBy": ["B"], "size": "S"},
        ]
        path = compute_critical_path(tasks)
        assert path == ["A", "B", "C"]

    def test_picks_heavier_branch(self):
        tasks = [
            {"id": "A", "blockedBy": [], "size": "S"},
            {"id": "B", "blockedBy": ["A"], "size": "L"},  # heavy branch
            {"id": "C", "blockedBy": ["A"], "size": "S"},  # light branch
            {"id": "D", "blockedBy": ["B", "C"], "size": "S"},
        ]
        path = compute_critical_path(tasks)
        # A->B->D is heavier (1+8+1=10) than A->C->D (1+1+1=3)
        assert "B" in path
        assert path == ["A", "B", "D"]

    def test_default_size_is_s(self):
        tasks = [
            {"id": "A", "blockedBy": []},  # no size key
            {"id": "B", "blockedBy": ["A"]},
        ]
        path = compute_critical_path(tasks)
        assert path == ["A", "B"]

    def test_raises_on_cycle(self):
        tasks = [
            {"id": "A", "blockedBy": ["B"], "size": "S"},
            {"id": "B", "blockedBy": ["A"], "size": "S"},
        ]
        with pytest.raises(ValueError):
            compute_critical_path(tasks)
