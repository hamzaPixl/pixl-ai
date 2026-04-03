"""Pydantic request/response models for workflow endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WorkflowSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    version: str | None = None
    tags: list[str] | None = None
    tier: str | None = None
    routing: dict[str, Any] | None = None


class WorkflowNodeDetail(BaseModel):
    id: str
    type: str
    task_config: dict[str, Any] | None = None
    gate_config: dict[str, Any] | None = None
    hook_config: dict[str, Any] | None = None
    metadata: dict[str, str] | None = None


class WorkflowEdgeDetail(BaseModel):
    to: str
    on: str
    condition: str | None = None


class WorkflowLoopDetail(BaseModel):
    id: str
    from_node: str
    to_node: str
    max_iterations: int | str = 3
    edge_trigger: str = "failure"


class WorkflowDetail(BaseModel):
    id: str
    name: str
    description: str | None = None
    tags: list[str] | None = None
    version: str | None = None
    tier: str | None = None
    routing: dict[str, Any] | None = None
    nodes: dict[str, WorkflowNodeDetail]
    edges: dict[str, list[WorkflowEdgeDetail]]
    loops: list[WorkflowLoopDetail] | None = None
    stages: list[dict[str, Any]] | None = None
    variables: dict[str, str] | None = None
