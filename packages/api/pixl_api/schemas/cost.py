"""Pydantic response models for cost endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class CostSummaryResponse(BaseModel):
    """Overall cost summary."""

    total_cost_usd: float = 0.0
    total_queries: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    top_model: str | None = None


class CostByModelResponse(BaseModel):
    """Cost breakdown for a single model."""

    model_name: str | None = None
    event_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class CostBySessionResponse(BaseModel):
    """Cost breakdown for a single session."""

    session_id: str
    event_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
