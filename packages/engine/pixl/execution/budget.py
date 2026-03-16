"""Budget enforcement — atomic cost recording with auto-pause.

After each node execution, record_cost() atomically increments the
monthly spend and checks against the budget limit. If exceeded,
the session is paused and a BUDGET_EXCEEDED event is emitted.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pixl.models.budget import BudgetConfig

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)

def get_budget(db: PixlDB) -> BudgetConfig:
    """Read budget config from the config table."""
    monthly = db.get_config("budget:monthly_usd", "0")
    return BudgetConfig(
        monthly_usd=float(monthly or "0"),
        spent_monthly_usd=db.cost_events.total_cost_for_month(),
    )

def set_budget(db: PixlDB, monthly_usd: float) -> None:
    """Set the monthly budget limit."""
    db.set_config("budget:monthly_usd", str(monthly_usd))

def record_cost(
    db: PixlDB,
    session_id: str,
    *,
    run_id: str | None = None,
    node_id: str | None = None,
    adapter_name: str | None = None,
    model_name: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> bool:
    """Record a cost event and check budget.

    Returns True if budget is still OK, False if exceeded.
    When exceeded, emits BUDGET_EXCEEDED event and pauses the session.
    """
    # Record the cost event
    db.cost_events.record(
        session_id,
        run_id=run_id,
        node_id=node_id,
        adapter_name=adapter_name,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )

    # Also update the heartbeat run if present
    if run_id:
        db.heartbeat_runs.increment_usage(
            run_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

    # Check budget
    budget = get_budget(db)

    # Emit warning at 80% threshold (once per session via best-effort)
    if (
        budget.monthly_usd > 0
        and not budget.is_exceeded
        and budget.spent_monthly_usd >= budget.monthly_usd * budget.alert_threshold
    ):
        try:
            db.events.emit(
                event_type="budget_warning",
                entity_type="session",
                entity_id=session_id,
                payload={
                    "spent_usd": budget.spent_monthly_usd,
                    "limit_usd": budget.monthly_usd,
                    "threshold": budget.alert_threshold,
                },
            )
        except Exception:
            pass

    if budget.is_exceeded:
        logger.warning(
            "Budget exceeded for session %s: $%.2f / $%.2f",
            session_id, budget.spent_monthly_usd, budget.monthly_usd,
        )

        try:
            db.events.emit(
                event_type="budget_exceeded",
                entity_type="session",
                entity_id=session_id,
                payload={
                    "spent_usd": budget.spent_monthly_usd,
                    "limit_usd": budget.monthly_usd,
                    "node_id": node_id,
                },
            )
        except Exception:
            logger.exception("Failed to emit budget_exceeded event")

        # Auto-pause the session
        from datetime import datetime

        try:
            db.sessions.update_session(
                session_id,
                paused_at=datetime.now().isoformat(),
                pause_reason="budget_exceeded",
            )
        except Exception:
            logger.exception("Failed to pause session %s on budget exceeded", session_id)

        return False

    return True
