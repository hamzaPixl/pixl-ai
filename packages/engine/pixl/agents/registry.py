"""Agent registry — parses crew agent markdown files into SDK AgentDefinitions."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from claude_agent_sdk import AgentDefinition

logger = logging.getLogger(__name__)


@dataclass
class CrewAgent:
    name: str
    description: str
    prompt: str
    model: str | None = None
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    max_turns: int = 50


class AgentRegistry:
    """Parses crew agent markdown files and maps them to SDK AgentDefinitions."""

    def __init__(self) -> None:
        self._agents: dict[str, CrewAgent] = {}
        self._definitions_cache: dict[str, AgentDefinition] | None = None

    def load_from_crew(self, crew_root: Path) -> None:
        self._definitions_cache = None  # Invalidate cache on reload
        """Parse all agents/*.md files from the crew directory."""
        agents_dir = crew_root / "agents"
        if not agents_dir.is_dir():
            logger.warning("Agents directory not found: %s", agents_dir)
            return
        for md_path in sorted(agents_dir.glob("*.md")):
            if agent := self._parse_agent_md(md_path):
                self._agents[agent.name] = agent

    def _parse_agent_md(self, path: Path) -> CrewAgent | None:
        """Parse YAML frontmatter + body from an agent markdown file."""
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not m:
            logger.warning("No frontmatter found in %s", path.name)
            return None
        try:
            meta = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            logger.warning("Invalid YAML in %s", path.name)
            return None
        if not isinstance(meta, dict) or "name" not in meta:
            return None
        raw_tools = meta.get("tools", [])
        tools = (
            [t.strip() for t in raw_tools.split(",")]
            if isinstance(raw_tools, str)
            else list(raw_tools)
        )
        model = meta.get("model")
        return CrewAgent(
            name=meta["name"],
            description=meta.get("description", ""),
            prompt=m.group(2).strip(),
            model=model if model != "inherit" else None,
            tools=tools,
            skills=meta.get("skills", []),
            max_turns=meta.get("maxTurns", 50),
        )

    def get_agent_definition(self, name: str) -> AgentDefinition | None:
        """Convert a crew agent to an SDK AgentDefinition."""
        agent = self._agents.get(name)
        if agent is None:
            return None
        tools = [t for t in agent.tools if t != "Agent"]
        from typing import Literal, cast

        return AgentDefinition(
            description=agent.description,
            prompt=agent.prompt,
            tools=tools or None,
            model=cast(Literal["sonnet", "opus", "haiku", "inherit"], agent.model)
            if agent.model is not None
            else None,
        )

    def get_all_definitions(self) -> dict[str, AgentDefinition]:
        """Return all agents as SDK AgentDefinitions (cached after first call)."""
        if self._definitions_cache is None:
            self._definitions_cache = {
                n: d for n in self._agents if (d := self.get_agent_definition(n)) is not None
            }
        return self._definitions_cache

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents)
