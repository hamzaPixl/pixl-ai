"""Task graph utilities: topological sort, cycle detection, critical path."""

from __future__ import annotations

import graphlib
from dataclasses import dataclass, field
from typing import Any


# Size weights for critical path calculation.
_SIZE_WEIGHT: dict[str, int] = {"S": 1, "M": 3, "L": 8}


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a task dependency graph."""

    valid: bool
    cycle_members: list[str] = field(default_factory=list)
    orphan_refs: dict[str, list[str]] = field(default_factory=dict)
    self_deps: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[str]:
        msgs: list[str] = []
        if self.cycle_members:
            ids = ", ".join(self.cycle_members)
            msgs.append(f"Dependency cycle detected involving: {ids}")
        for task_id, refs in self.orphan_refs.items():
            msgs.append(f"Task {task_id} references unknown IDs: {', '.join(refs)}")
        for task_id in self.self_deps:
            msgs.append(f"Task {task_id} depends on itself")
        return msgs


def _extract_graph(tasks: list[dict[str, Any]]) -> tuple[dict[str, set[str]], set[str]]:
    """Extract adjacency sets from task list. Returns (deps_map, all_ids)."""
    all_ids = {t["id"] for t in tasks}
    deps: dict[str, set[str]] = {}
    for t in tasks:
        blocked_by = set(t.get("blockedBy") or [])
        deps[t["id"]] = blocked_by
    return deps, all_ids


def validate_task_graph(tasks: list[dict[str, Any]]) -> ValidationResult:
    """Validate a task dependency graph for cycles, orphan refs, and self-deps."""
    if not tasks:
        return ValidationResult(valid=True)

    deps, all_ids = _extract_graph(tasks)

    # Check self-dependencies.
    self_deps = [tid for tid, blocked in deps.items() if tid in blocked]

    # Check orphan references (blockedBy ID not in task list).
    orphan_refs: dict[str, list[str]] = {}
    for tid, blocked in deps.items():
        orphans = sorted(blocked - all_ids)
        if orphans:
            orphan_refs[tid] = orphans

    # Check cycles using graphlib.
    cycle_members: list[str] = []
    try:
        ts = graphlib.TopologicalSorter(deps)
        ts.prepare()
    except graphlib.CycleError as exc:
        # exc.args[1] contains the cycle path.
        cycle_members = sorted(set(exc.args[1])) if len(exc.args) > 1 else []

    valid = not cycle_members and not orphan_refs and not self_deps
    return ValidationResult(
        valid=valid,
        cycle_members=cycle_members,
        orphan_refs=orphan_refs,
        self_deps=self_deps,
    )


def compute_execution_order(tasks: list[dict[str, Any]]) -> list[str]:
    """Return topologically sorted task IDs. Raises ValueError on cycles."""
    if not tasks:
        return []

    deps, _ = _extract_graph(tasks)

    try:
        ts = graphlib.TopologicalSorter(deps)
        return list(ts.static_order())
    except graphlib.CycleError as exc:
        cycle = exc.args[1] if len(exc.args) > 1 else []
        raise ValueError(f"Dependency cycle detected: {cycle}") from exc


def compute_critical_path(tasks: list[dict[str, Any]]) -> list[str]:
    """Compute the critical path (longest weighted chain) through the task graph.

    Weights: S=1, M=3, L=8 (from task["size"]).
    Returns ordered list of task IDs on the critical path.
    """
    if not tasks:
        return []

    order = compute_execution_order(tasks)
    task_map = {t["id"]: t for t in tasks}

    # Longest-path DP: dist[node] = max weighted distance to reach node.
    dist: dict[str, int] = {}
    predecessor: dict[str, str | None] = {}

    for tid in order:
        weight = _SIZE_WEIGHT.get(task_map[tid].get("size", "S"), 1)
        blocked_by = task_map[tid].get("blockedBy") or []
        if not blocked_by:
            dist[tid] = weight
            predecessor[tid] = None
        else:
            best_pred = max(
                (dep for dep in blocked_by if dep in dist),
                key=lambda d: dist[d],
                default=None,
            )
            if best_pred is not None:
                dist[tid] = dist[best_pred] + weight
                predecessor[tid] = best_pred
            else:
                dist[tid] = weight
                predecessor[tid] = None

    if not dist:
        return []

    # Trace back from the node with maximum distance.
    end = max(dist, key=lambda k: dist[k])
    path: list[str] = []
    current: str | None = end
    while current is not None:
        path.append(current)
        current = predecessor.get(current)
    path.reverse()
    return path
