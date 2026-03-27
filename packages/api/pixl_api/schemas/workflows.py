"""Pydantic request/response models for workflow endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WorkflowSummary(BaseModel):
    id: str
    name: str
    description: str | None = None


class WorkflowDetail(BaseModel):
    id: str
    name: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    metadata: dict[str, Any] | None = None
