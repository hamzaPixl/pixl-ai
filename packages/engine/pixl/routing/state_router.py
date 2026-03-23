"""State-aware routing — adjusts workflow selection based on entity state.

Wraps the base PromptClassifier to enrich routing decisions with
backlog context. When existing entities match the prompt, the router
can suggest more appropriate workflows based on current state.

Examples:
    - Prompt about a feature that's already in_progress → suggest "resume"
    - Prompt about a blocked feature → suggest "debug" workflow
    - Prompt about an epic that's already decomposed → suggest "tdd"
    - New prompt with no matching entities → fall through to base classifier
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pixl.routing.models import RouterResult, WorkKind, get_allowed_workflows

# State context — what the router knows about current backlog


@dataclass
class EntityMatch:
    """An entity from the backlog that appears related to the prompt."""

    entity_id: str
    entity_type: str  # "feature", "epic", "roadmap"
    title: str
    status: str
    score: float  # How well the entity matches the prompt (0.0–1.0)


@dataclass
class StateContext:
    """Backlog state relevant to a routing decision."""

    matches: list[EntityMatch] = field(default_factory=list)
    blocked_features: list[str] = field(default_factory=list)
    in_progress_count: int = 0
    unblocked_ready: list[str] = field(default_factory=list)

    @property
    def best_match(self) -> EntityMatch | None:
        return self.matches[0] if self.matches else None

    @property
    def has_blocked(self) -> bool:
        return len(self.blocked_features) > 0


# Workflow suggestion rules

# Status → suggested workflow override
_WORKFLOW_BY_STATUS: dict[str, dict[str, str]] = {
    "feature": {
        "backlog": "tdd",
        "planned": "tdd",
        "in_progress": "simple",  # Resume with simple workflow
        "blocked": "debug",
        "review": "simple",
        "failed": "debug",
    },
    "epic": {
        "drafting": "decompose",
        "decomposed": "tdd",
        "in_progress": "tdd",
        "failed": "debug",
    },
    "roadmap": {
        "drafting": "roadmap",
        "planned": "roadmap",
        "in_progress": "roadmap",
    },
}


def suggest_workflow_for_state(entity_type: str, status: str) -> str | None:
    """Suggest a workflow based on entity type and current status.

    Returns workflow ID or None if no suggestion.
    """
    type_rules = _WORKFLOW_BY_STATUS.get(entity_type, {})
    suggestion = type_rules.get(status)
    if suggestion and suggestion in get_allowed_workflows():
        return suggestion
    return None


def map_entity_type_to_work_kind(entity_type: str) -> WorkKind:
    """Map entity type string to WorkKind enum."""
    return {
        "feature": WorkKind.FEATURE,
        "epic": WorkKind.EPIC,
        "roadmap": WorkKind.ROADMAP,
    }.get(entity_type, WorkKind.FEATURE)


# Title similarity (lightweight, no external deps)


def _normalize(text: str) -> set[str]:
    """Extract lowercase word tokens from text."""
    import re

    return set(re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()))


def title_similarity(prompt: str, title: str) -> float:
    """Jaccard similarity between prompt and entity title tokens."""
    prompt_tokens = _normalize(prompt)
    title_tokens = _normalize(title)
    if not prompt_tokens or not title_tokens:
        return 0.0
    intersection = prompt_tokens & title_tokens
    union = prompt_tokens | title_tokens
    return len(intersection) / len(union) if union else 0.0


# StateAwareRouter


class StateAwareRouter:
    """Enriches routing decisions with backlog state context.

    Scans the existing backlog for entities that match the prompt,
    then adjusts the suggested workflow based on their current state.

    Usage:
        router = StateAwareRouter(project_path)
        context = router.build_context("Fix the auth login bug")
        adjustment = router.adjust(base_result, context)
    """

    # Minimum similarity to consider an entity a match
    MATCH_THRESHOLD = 0.3

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def _get_store(self) -> Any:
        """Lazy-load the backlog store."""
        from pixl.storage.backlog_adapter import BacklogStoreAdapter

        adapter = BacklogStoreAdapter(self.project_path)
        if not adapter.exists():
            return None
        return adapter

    def build_context(self, prompt: str) -> StateContext:
        """Scan the backlog and build state context for routing.

        Finds entities whose titles are similar to the prompt,
        counts blocked/in-progress entities, and identifies
        ready-to-execute features.
        """
        store = self._get_store()
        if store is None:
            return StateContext()

        ctx = StateContext()

        # Scan features
        try:
            features = store.list_all()
        except Exception:
            features = []

        for feat in features:
            sim = title_similarity(prompt, feat.title)
            if sim >= self.MATCH_THRESHOLD:
                ctx.matches.append(
                    EntityMatch(
                        entity_id=feat.id,
                        entity_type="feature",
                        title=feat.title,
                        status=feat.status.value
                        if hasattr(feat.status, "value")
                        else str(feat.status),
                        score=sim,
                    )
                )

            status = feat.status.value if hasattr(feat.status, "value") else str(feat.status)
            if status == "blocked":
                ctx.blocked_features.append(feat.id)
            if status == "in_progress":
                ctx.in_progress_count += 1

        # Scan epics
        backlog = None
        try:
            backlog = store.load()
            epics = backlog.epics
        except Exception:
            epics = []

        for epic in epics:
            sim = title_similarity(prompt, epic.title)
            if sim >= self.MATCH_THRESHOLD:
                status = epic.status.value if hasattr(epic.status, "value") else str(epic.status)
                ctx.matches.append(
                    EntityMatch(
                        entity_id=epic.id,
                        entity_type="epic",
                        title=epic.title,
                        status=status,
                        score=sim,
                    )
                )

        # Scan roadmaps
        try:
            roadmaps = backlog.roadmaps if backlog else []
        except Exception:
            roadmaps = []

        for rm in roadmaps:
            sim = title_similarity(prompt, rm.title)
            if sim >= self.MATCH_THRESHOLD:
                status = rm.status.value if hasattr(rm.status, "value") else str(rm.status)
                ctx.matches.append(
                    EntityMatch(
                        entity_id=rm.id,
                        entity_type="roadmap",
                        title=rm.title,
                        status=status,
                        score=sim,
                    )
                )

        ctx.matches.sort(key=lambda m: m.score, reverse=True)

        return ctx

    def adjust(
        self,
        base_result: RouterResult,
        context: StateContext,
    ) -> tuple[RouterResult, list[str]]:
        """Adjust a RouterResult based on state context.

        Returns (adjusted_result, adjustment_reasons).
        If no adjustment is needed, returns the base_result unchanged.
        """
        reasons: list[str] = []

        if not context.matches:
            return base_result, reasons

        best = context.best_match
        assert best is not None

        suggested = suggest_workflow_for_state(best.entity_type, best.status)
        if suggested and suggested != base_result.suggested_workflow:
            reasons.append(
                f"Matched existing {best.entity_type} '{best.entity_id}' "
                f"(status: {best.status}) — suggesting '{suggested}' workflow"
            )

            adjusted = RouterResult(
                kind=map_entity_type_to_work_kind(best.entity_type),
                confidence=base_result.confidence,
                title=base_result.title,
                why=base_result.why + reasons,
                suggested_workflow=suggested,
                estimated_features=base_result.estimated_features,
                risk_flags=base_result.risk_flags,
                next_inputs=base_result.next_inputs,
            )
            return adjusted, reasons

        # Even without workflow change, flag relevant state info
        if context.has_blocked:
            reasons.append(f"Note: {len(context.blocked_features)} blocked feature(s) in backlog")

        if context.in_progress_count > 0:
            reasons.append(f"Note: {context.in_progress_count} feature(s) currently in progress")

        return base_result, reasons
