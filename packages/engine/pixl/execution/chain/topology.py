"""DAG topology utilities: topological sort, descendant traversal, wave detection."""

from __future__ import annotations

from typing import Any

from pixl.execution.chain_constants import CHAIN_TERMINAL_STATES

def toposort_ready_nodes(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (runnable_nodes, newly_blocked_node_ids).

    A node is runnable if:
    - status == 'pending'
    - all predecessor nodes are 'completed'

    A node is blocked if:
    - status == 'pending'
    - any predecessor is in a terminal non-success state
    """
    by_id = {str(n.get("node_id")): n for n in nodes}
    preds: dict[str, set[str]] = {node_id: set() for node_id in by_id}
    for edge in edges:
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if src in preds and dst in preds and src and dst:
            preds[dst].add(src)

    runnable: list[dict[str, Any]] = []
    blocked: list[str] = []
    for node_id, node in by_id.items():
        if node.get("status") != "pending":
            continue
        predecessors = preds.get(node_id, set())
        if not predecessors:
            runnable.append(node)
            continue
        pred_states = [by_id[p].get("status") for p in predecessors if p in by_id]
        if any(s in {"failed", "blocked", "cancelled"} for s in pred_states):
            blocked.append(node_id)
            continue
        if all(s in {"completed", "refined"} for s in pred_states):
            runnable.append(node)

    # Deterministic ordering: wave -> parallel_group -> node_id
    runnable.sort(
        key=lambda n: (
            int(n.get("wave", 0) or 0),
            int(n.get("parallel_group", 0) or 0),
            str(n.get("node_id", "")),
        )
    )
    return runnable, blocked

def descendants(
    *,
    start_node_id: str,
    edges: list[dict[str, str]],
) -> list[str]:
    adj: dict[str, set[str]] = {}
    for edge in edges:
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if not src or not dst:
            continue
        adj.setdefault(src, set()).add(dst)

    seen: set[str] = set()
    queue: list[str] = [start_node_id]
    while queue:
        current = queue.pop(0)
        for child in sorted(adj.get(current, set())):
            if child in seen:
                continue
            seen.add(child)
            queue.append(child)
    return sorted(seen)

def detect_completed_wave(nodes: list[dict[str, Any]]) -> int | None:
    """Return wave number if all nodes in that wave are terminal and next wave has pending nodes."""
    waves: dict[int, list[dict[str, Any]]] = {}
    for node in nodes:
        wave = int(node.get("wave", 0) or 0)
        waves.setdefault(wave, []).append(node)

    terminal = CHAIN_TERMINAL_STATES
    sorted_waves = sorted(waves.keys())

    for i, wave_num in enumerate(sorted_waves):
        wave_nodes = waves[wave_num]
        if not all(str(n.get("status")) in terminal for n in wave_nodes):
            continue
        if i + 1 < len(sorted_waves):
            next_wave = sorted_waves[i + 1]
            if any(str(n.get("status")) == "pending" for n in waves[next_wave]):
                return wave_num
    return None
