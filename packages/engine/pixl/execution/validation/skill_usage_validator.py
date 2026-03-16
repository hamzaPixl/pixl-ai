"""Skill and agent usage validation for contract enforcement.

Scans a session transcript (or extracted tool-use log) for evidence
that required skills and agents were invoked during the stage.
"""

from __future__ import annotations

import json
from pathlib import Path

from pixl.execution.contract_constants import RULE_REQUIRED_AGENTS, RULE_REQUIRED_SKILLS
from pixl.execution.validation.models import ContractValidationResult, ContractViolation

def check_required_skills(
    required_skills: list[str],
    transcript_path: Path | None,
    result: ContractValidationResult,
) -> None:
    """Check that required skills were invoked in the session transcript.

    Scans the JSONL transcript for Skill tool invocations and checks
    that each required skill name appears at least once.

    Args:
        required_skills: Skill names that must appear (e.g. ["/ddd-pattern"])
        transcript_path: Path to the session JSONL transcript file
        result: ContractValidationResult to accumulate violations
    """
    if not required_skills:
        return

    invoked_skills = _extract_invoked_skills(transcript_path)

    for skill in required_skills:
        normalized = skill.lstrip("/")
        if not any(normalized == s.lstrip("/") for s in invoked_skills):
            result.violations.append(
                ContractViolation(
                    rule=RULE_REQUIRED_SKILLS,
                    message=f"Required skill not invoked: {skill}",
                )
            )

def check_required_agents(
    required_agents: list[str],
    transcript_path: Path | None,
    result: ContractValidationResult,
) -> None:
    """Check that required agents were used in the session transcript.

    Scans the JSONL transcript for Agent tool invocations and checks
    that each required subagent_type appears at least once.

    Args:
        required_agents: Agent subagent_type values (e.g. ["pixl-crew:backend-engineer"])
        transcript_path: Path to the session JSONL transcript file
        result: ContractValidationResult to accumulate violations
    """
    if not required_agents:
        return

    invoked_agents = _extract_invoked_agents(transcript_path)

    for agent in required_agents:
        if agent not in invoked_agents:
            result.violations.append(
                ContractViolation(
                    rule=RULE_REQUIRED_AGENTS,
                    message=f"Required agent not used: {agent}",
                )
            )

def _extract_invoked_skills(transcript_path: Path | None) -> set[str]:
    """Extract skill names from Skill tool invocations in transcript."""
    if transcript_path is None or not transcript_path.exists():
        return set()

    skills: set[str] = set()
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Look for Skill tool use in assistant messages
                _extract_skills_from_entry(entry, skills)
    except OSError:
        pass

    return skills

def _extract_skills_from_entry(entry: dict, skills: set[str]) -> None:
    """Extract skill names from a single transcript entry."""
    # Claude Code transcripts store tool uses in content blocks
    content = entry.get("content")
    if not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue
        # tool_use blocks have type="tool_use", name="Skill", input={skill: "..."}
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            tool_input = block.get("input") or {}
            skill_name = tool_input.get("skill")
            if isinstance(skill_name, str) and skill_name:
                skills.add(skill_name)

def _extract_invoked_agents(transcript_path: Path | None) -> set[str]:
    """Extract agent subagent_type values from Agent tool invocations."""
    if transcript_path is None or not transcript_path.exists():
        return set()

    agents: set[str] = set()
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                _extract_agents_from_entry(entry, agents)
    except OSError:
        pass

    return agents

def _extract_agents_from_entry(entry: dict, agents: set[str]) -> None:
    """Extract agent types from a single transcript entry."""
    content = entry.get("content")
    if not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == "Agent":
            tool_input = block.get("input") or {}
            agent_type = tool_input.get("subagent_type")
            if isinstance(agent_type, str) and agent_type:
                agents.add(agent_type)
