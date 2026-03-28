"""Agent endpoints: list configured agents and available models."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB
from pixl_api.schemas.agents import AgentResponse, ModelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Dynamic agent loading from crew/agents/*.md
# ---------------------------------------------------------------------------

_FALLBACK_AGENTS: list[dict[str, Any]] = [
    {
        "name": "orchestrator",
        "description": "Multi-agent coordination",
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
        "name": "frontend-engineer",
        "description": "React/Next.js, shadcn/ui",
        "model": None,
        "tools": [],
        "max_turns": 50,
    },
]

_cached_agents: list[dict[str, Any]] | None = None

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract key-value pairs from YAML frontmatter (simple single-line values)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        # Skip continuation lines (indented or starting with special YAML chars)
        if not line or line[0] in (" ", "\t", "-", "#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip trailing YAML block indicators like >
        if value == ">":
            continue
        result[key] = value
    return result


def _extract_description(text: str) -> str:
    """Extract the first sentence of the description from frontmatter."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return ""
    fm = match.group(1)
    # Find description field
    desc_match = re.search(r"^description:\s*>?\s*\n([ \t]+\S.*)", fm, re.MULTILINE)
    if desc_match:
        # First non-empty indented line after description:
        first_line = desc_match.group(1).strip()
        # Take up to the first period or dash that starts a new concept
        period_idx = first_line.find(" -- ")
        if period_idx == -1:
            period_idx = first_line.find(" — ")
        if period_idx != -1:
            first_line = first_line[:period_idx]
        return first_line.rstrip(".")
    # Inline description
    desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if desc_match:
        return desc_match.group(1).strip().rstrip(".")
    return ""


def _load_agents_from_crew() -> list[dict[str, Any]]:
    """Load agent definitions from crew/agents/*.md files.

    Falls back to a minimal hardcoded list if the crew directory is not found.
    """
    agents_dir: Path | None = None
    try:
        from pixl_cli.crew import get_crew_root

        agents_dir = get_crew_root() / "agents"
    except (ImportError, FileNotFoundError):
        agents_dir = None

    if agents_dir is None or not agents_dir.is_dir():
        logger.info("Crew agents directory not found, using fallback agent list")
        return list(_FALLBACK_AGENTS)

    agents: list[dict[str, Any]] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        fm = _parse_frontmatter(text)
        name = fm.get("name", md_file.stem)
        model_val = fm.get("model")
        if model_val in ("inherit", "null", "None", ""):
            model_val = None

        tools_raw = fm.get("tools", "")
        tools = [t.strip() for t in tools_raw.split(",") if t.strip()] if tools_raw else []

        max_turns_raw = fm.get("maxTurns", "50")
        try:
            max_turns = int(max_turns_raw)
        except ValueError:
            max_turns = 50

        description = _extract_description(text)
        if not description:
            description = name.replace("-", " ").title()

        agents.append(
            {
                "name": name,
                "description": description,
                "model": model_val,
                "tools": tools,
                "max_turns": max_turns,
            }
        )

    if not agents:
        logger.warning("No agents found in %s, using fallback list", agents_dir)
        return list(_FALLBACK_AGENTS)

    return agents


def _get_agents() -> list[dict[str, Any]]:
    """Return the cached agent list, loading on first access."""
    global _cached_agents  # noqa: PLW0603
    if _cached_agents is None:
        _cached_agents = _load_agents_from_crew()
    return _cached_agents


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
    return _get_agents()


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
    for agent in _get_agents():
        if agent["name"] == agent_name:
            return {**agent, "model": model}
    from pixl_api.errors import EntityNotFoundError

    raise EntityNotFoundError("agent", agent_name)
