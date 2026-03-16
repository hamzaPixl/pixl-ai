"""Agent performance metrics models.

This module defines data models for capturing detailed agent performance
metrics that extend beyond basic cost tracking to include operational
insights like success rates, error types, and timing data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentMetrics:
    """Comprehensive performance metrics for individual agent executions.

    Extends basic cost tracking with operational context including
    which agent executed, which workflow node, success/failure status,
    and detailed timing information.
    """

    # Execution context (required fields)
    agent_name: str
    model_name: str
    session_id: str
    node_id: str
    started_at: datetime

    # Optional execution context
    feature_id: str | None = None
    completed_at: datetime | None = None

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Cost
    total_cost_usd: float = 0.0

    # Outcome
    success: bool = True
    error_type: str | None = None
    error_message: str | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds."""
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()
