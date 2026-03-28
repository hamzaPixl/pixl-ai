"""Pydantic request/response models for chain endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChainNodeResponse(BaseModel):
    """Summary of a chain node."""

    node_id: str
    feature_id: str | None = None
    feature_ref: str | None = None
    wave: int = 0
    parallel_group: int = 0
    owner: str | None = None
    risk_class: str | None = None
    estimate_points: int | None = None
    status: str | None = None
    session_id: str | None = None
    error: str | None = None


class ChainResponse(BaseModel):
    """Summary of an execution chain."""

    id: str
    epic_id: str | None = None
    mode: str | None = None
    status: str | None = None
    max_parallel: int | None = None
    failure_policy: str | None = None
    stop_on_failure: bool = False
    node_counts: dict[str, int] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ChainDetailResponse(BaseModel):
    """Full chain detail including nodes and edges."""

    chain_id: str
    epic_id: str | None = None
    mode: str | None = None
    status: str | None = None
    max_parallel: int | None = None
    failure_policy: str | None = None
    stop_on_failure: bool = False
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    waves: list[list[Any]] = []
    created_at: str | None = None
    updated_at: str | None = None


class CreateChainRequest(BaseModel):
    """Request body for creating a chain plan."""

    epic_id: str = Field(description="Epic to create chain for")
    workflow_id: str = Field(default="tdd", description="Workflow template to use")
    max_parallel: int = Field(default=1, ge=1, description="Max parallel executions")
    stop_on_failure: bool = Field(default=True, description="Stop chain on first failure")


class StartChainResponse(BaseModel):
    """Response after starting a chain."""

    chain_id: str
    status: str
    message: str
