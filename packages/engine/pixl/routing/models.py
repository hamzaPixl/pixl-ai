"""Router models for prompt classification."""

from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class WorkKind(StrEnum):
    """Classification of work scope."""

    FEATURE = "feature"
    BUG = "bug"
    EPIC = "epic"
    ROADMAP = "roadmap"


# Fallback set used when YAML loading fails or during testing
_FALLBACK_WORKFLOWS = {"tdd", "decompose", "roadmap", "simple", "debug"}

_allowed_workflows_cache: set[str] | None = None


def get_allowed_workflows() -> set[str]:
    """Return workflow IDs where ``routing.auto_route`` is true.

    Results are cached for the lifetime of the process.  Falls back to
    ``_FALLBACK_WORKFLOWS`` if YAML loading fails (e.g. no project context).
    """
    global _allowed_workflows_cache
    if _allowed_workflows_cache is not None:
        return _allowed_workflows_cache

    try:
        from pathlib import Path

        bundled_dir = Path(__file__).parent.parent / "assets" / "workflows"
        allowed: set[str] = set()
        if bundled_dir.exists():
            from pixl.models.workflow_config import WorkflowConfigYaml

            for yaml_file in bundled_dir.glob("*.yaml"):
                try:
                    config = WorkflowConfigYaml.from_yaml_file(yaml_file)
                    if config.routing and config.routing.auto_route:
                        allowed.add(config.id)
                except Exception:
                    logger.debug("Skipping unreadable workflow %s", yaml_file.name)
        if allowed:
            _allowed_workflows_cache = allowed
            return _allowed_workflows_cache
    except Exception:
        logger.debug("Failed to load workflows from YAML, using fallback set")

    _allowed_workflows_cache = _FALLBACK_WORKFLOWS.copy()
    return _allowed_workflows_cache


# Keep backward-compatible constant pointing at fallback (tests may import it)
ALLOWED_WORKFLOWS = _FALLBACK_WORKFLOWS


class RouterResult(BaseModel):
    """Result of prompt classification by the router."""

    kind: WorkKind
    confidence: float = Field(..., ge=0.0, le=1.0)
    title: str = Field(..., min_length=1, max_length=300)
    why: list[str] = Field(..., min_length=1)
    suggested_workflow: str
    estimated_features: int = Field(default=1, ge=1)
    risk_flags: list[str] = Field(default_factory=list)
    next_inputs: dict[str, str] = Field(default_factory=dict)
    suggested_sub_workflows: list[str] = Field(
        default_factory=list,
        description="Task-tier sub-workflows the classifier thinks are relevant",
    )

    @field_validator("suggested_workflow")
    @classmethod
    def validate_workflow(cls, v: str) -> str:
        allowed = get_allowed_workflows()
        if v not in allowed:
            raise ValueError(f"Unknown workflow '{v}'. Allowed: {sorted(allowed)}")
        return v
