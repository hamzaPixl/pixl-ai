"""Constants for chain execution status tracking.

Centralizes terminal state sets and node status values used across
the chain runner and related modules.
"""

from __future__ import annotations

# Terminal states for chain nodes — a node in any of these states
# will not be scheduled for execution.
CHAIN_TERMINAL_STATES: frozenset[str] = frozenset(
    {
        "completed",
        "failed",
        "blocked",
        "cancelled",
        "refined",
    }
)

# Individual node status constants
CHAIN_NODE_PENDING = "pending"
CHAIN_NODE_RUNNING = "running"
CHAIN_NODE_COMPLETED = "completed"
CHAIN_NODE_FAILED = "failed"
CHAIN_NODE_BLOCKED = "blocked"
CHAIN_NODE_CANCELLED = "cancelled"
CHAIN_NODE_REFINED = "refined"

# Chain-level status values
CHAIN_STATUS_RUNNING = "running"
CHAIN_STATUS_PAUSED = "paused"
CHAIN_STATUS_COMPLETED = "completed"
CHAIN_STATUS_FAILED = "failed"
