"""Agent endpoints: list configured agents and available models."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB
from pixl_api.schemas.agents import AgentResponse, ModelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/agents", tags=["agents"])

# Static agent list derived from crew/agents/*.md
# AgentRegistry requires filesystem access to crew markdown files which may
# not be available from the API process. We expose the canonical list here.
_KNOWN_AGENTS: list[dict[str, Any]] = [
    {
        "name": "orchestrator",
        "description": "Multi-agent coordination",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "architect",
        "description": "System design, DDD",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "product-owner",
        "description": "Task planning, sprints",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "tech-lead",
        "description": "Code review, quality gates",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "frontend-engineer",
        "description": "React/Next.js, shadcn/ui",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "backend-engineer",
        "description": "TypeScript/Python backend",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "fullstack-engineer",
        "description": "End-to-end across API boundary",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "qa-engineer",
        "description": "Testing, browser verification",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "devops-engineer",
        "description": "Docker, CI/CD, deployment",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "security-engineer",
        "description": "OWASP audits, RBAC",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "explorer",
        "description": "Fast codebase exploration",
        "model": "haiku",
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "onboarding-agent",
        "description": "Client project onboarding",
        "model": "haiku",
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "build-error-resolver",
        "description": "Surgical build/type error fixes",
        "model": "sonnet",
        "tools": [],
        "max_turns": 50,
    },
    {
        "name": "doc-updater",
        "description": "Keep docs in sync with code",
        "model": "haiku",
        "tools": [],
        "max_turns": 50,
    },
]

_KNOWN_MODELS: list[dict[str, Any]] = [
    {
        "id": "sonnet",
        "provider": "anthropic",
        "description": "Claude Sonnet — balanced speed and quality",
    },
    {"id": "opus", "provider": "anthropic", "description": "Claude Opus — highest capability"},
    {
        "id": "haiku",
        "provider": "anthropic",
        "description": "Claude Haiku — fastest, lightweight tasks",
    },
]


@router.get("", response_model=list[AgentResponse])
async def list_agents(db: ProjectDB) -> list[dict[str, Any]]:
    """List configured agents for a project."""
    return _KNOWN_AGENTS


@router.get("/models", response_model=list[ModelResponse])
async def list_models(db: ProjectDB) -> list[dict[str, Any]]:
    """List available LLM models."""
    return _KNOWN_MODELS


# Agent model configuration endpoints


@router.get("/classification-model")
async def get_classification_model(db: ProjectDB) -> dict[str, Any]:
    """Get the current classification model config."""
    try:
        val = await asyncio.to_thread(db.config.get, "classification_model")
    except Exception:
        val = None
    return {"model": val or "sonnet", "provider": "anthropic"}


@router.put("/classification-model")
async def update_classification_model(db: ProjectDB, body: dict[str, Any]) -> dict[str, Any]:
    """Update the classification model."""
    model = body.get("model", "sonnet")
    try:
        await asyncio.to_thread(db.config.set, "classification_model", model)
    except Exception:
        pass
    return {"model": model, "provider": "anthropic"}


@router.get("/session-report-model")
async def get_session_report_model(db: ProjectDB) -> dict[str, Any]:
    """Get the current session report model config."""
    try:
        val = await asyncio.to_thread(db.config.get, "session_report_model")
    except Exception:
        val = None
    return {"model": val or "sonnet", "provider": "anthropic"}


@router.put("/session-report-model")
async def update_session_report_model(db: ProjectDB, body: dict[str, Any]) -> dict[str, Any]:
    """Update the session report model."""
    model = body.get("model", "sonnet")
    try:
        await asyncio.to_thread(db.config.set, "session_report_model", model)
    except Exception:
        pass
    return {"model": model, "provider": "anthropic"}


@router.put("/{agent_name}/model")
async def update_agent_model(
    db: ProjectDB, agent_name: str, body: dict[str, Any]
) -> dict[str, Any]:
    """Update the model for a specific agent."""
    model = body.get("model")
    try:
        await asyncio.to_thread(db.config.set, f"agent_model:{agent_name}", model)
    except Exception:
        pass
    # Find the agent and return updated info
    for agent in _KNOWN_AGENTS:
        if agent["name"] == agent_name:
            return {**agent, "model": model}
    from pixl_api.errors import EntityNotFoundError

    raise EntityNotFoundError("agent", agent_name)
