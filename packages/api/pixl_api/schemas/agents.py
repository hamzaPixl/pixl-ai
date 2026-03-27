"""Pydantic response models for agent endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Summary of a configured agent."""

    name: str
    description: str
    model: str | None = None
    tools: list[str] = []
    max_turns: int = 50


class ModelResponse(BaseModel):
    """Available LLM model entry."""

    id: str
    provider: str
    description: str | None = None
