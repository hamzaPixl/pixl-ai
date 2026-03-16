"""Budget and cost tracking models.

Tracks per-run cost events and enforces monthly budget limits.
When budget is exceeded, sessions are auto-paused with a BUDGET_EXCEEDED event.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CostEvent(BaseModel):
    """A single cost incurrence from adapter execution."""

    id: int | None = None
    session_id: str
    run_id: str | None = None
    node_id: str | None = None
    adapter_name: str | None = None
    model_name: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)


class BudgetConfig(BaseModel):
    """Monthly budget configuration."""

    monthly_usd: float = 0.0  # 0 = unlimited
    alert_threshold: float = 0.8  # Soft warning at 80%
    spent_monthly_usd: float = 0.0

    @property
    def remaining_usd(self) -> float:
        if self.monthly_usd <= 0:
            return float("inf")
        return max(0.0, self.monthly_usd - self.spent_monthly_usd)

    @property
    def is_exceeded(self) -> bool:
        if self.monthly_usd <= 0:
            return False
        return self.spent_monthly_usd >= self.monthly_usd


def check_budget(budget: BudgetConfig, additional_cost: float = 0.0) -> bool:
    """Return True if budget allows the additional cost."""
    if budget.monthly_usd <= 0:
        return True
    return (budget.spent_monthly_usd + additional_cost) < budget.monthly_usd
