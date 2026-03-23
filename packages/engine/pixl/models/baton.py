"""Baton model for internal workflow progress tracking.

The baton is a structured packet that the executor uses to track
workflow progress between stages. It is NOW included in prompts sent to
agents (via Baton.to_prompt_section()) making goal anchoring, decision
history, and constraints visible to agents.

The baton serves for:
- Artifact selection: work_scope guides which artifacts the context compiler
  considers for inclusion.
- Progress tracking: current_state and decision_log record what happened.
- Audit trail: baton_history on the session captures state at each stage.
- Agent context: Agents see the goal, decisions, constraints in their prompts.

Agents update the baton by including baton_patch in the payload field of
their <pixl_output> envelope.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArtifactRef(BaseModel):
    """Lightweight artifact pointer (no content).

    Used in the baton to reference artifacts without including their content.
    The context compiler uses these refs to decide what to include in prompts.
    """

    id: str = Field(description="Artifact ID (art-XXXX)")
    hash: str = Field(description="SHA256 hash prefix (first 16 chars)")
    type: str = Field(description="Artifact type: document, code, test, plan, etc.")
    summary_ref: str | None = Field(
        default=None,
        description="Path to cached summary file relative to artifacts_dir",
    )

    def to_inline(self) -> str:
        """Render as compact inline string for prompt injection."""
        parts = [f"{self.id} ({self.type}, {self.hash[:12]}...)"]
        if self.summary_ref:
            parts.append(f"summary: {self.summary_ref}")
        return " | ".join(parts)


class Baton(BaseModel):
    """Internal tracking state for workflow progress.

    The baton is used by the executor to track progress, guide artifact
    selection, and maintain an audit trail. It IS rendered into agent
    prompts via to_prompt_section() — agents update it via baton_patch
    in the <pixl_output> envelope payload.
    """

    goal: str = Field(description="One-sentence goal for this workflow")
    current_state: list[str] = Field(
        default_factory=list,
        description="What's true right now (3-8 bullets)",
    )
    decision_log: list[str] = Field(
        default_factory=list,
        description="Last 5 decisions, each 1 line",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved questions (max 5)",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Hard rules that must be respected (max 10)",
    )
    artifacts: list[ArtifactRef] = Field(
        default_factory=list,
        description="Artifact references (refs only, no content)",
    )
    work_scope: list[str] = Field(
        default_factory=list,
        description="Files/modules touched or planned",
    )
    acceptance: list[str] = Field(
        default_factory=list,
        description="Tests/checks that must pass",
    )
    stage_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Stage-targeted hints, e.g. {'implement': 'Focus on task 1 only'}",
    )
    quality_signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated quality data: test_count, lint_issues, review_score",
    )

    def to_prompt_section(self, *, emphasis: list[str] | None = None) -> str:
        """Render baton as a markdown section for prompt injection.

        Args:
            emphasis: Optional list of baton field names to render in full detail.
                      Non-emphasized fields are rendered in compact single-line format.
                      goal and current_state are always rendered in full.
                      Valid fields: constraints, acceptance, decision_log,
                      open_questions, work_scope, stage_hints, quality_signals.

        Returns:
            Markdown-formatted baton context.
        """
        emphasis_set = set(emphasis) if emphasis else set()
        lines = ["## Baton (Handoff Context)", ""]
        lines.append(f"**Goal:** {self.goal}")
        lines.append("")

        # current_state: always full detail
        if self.current_state:
            lines.append("**Current State:**")
            for item in self.current_state[:8]:
                lines.append(f"- {item}")
            lines.append("")

        # List fields with emphasis support
        _list_fields: list[tuple[str, str, list[str], int]] = [
            ("decision_log", "Recent Decisions", self.decision_log[-5:], 5),
            ("open_questions", "Open Questions", self.open_questions[:5], 5),
            ("constraints", "Constraints", self.constraints[:10], 10),
            ("acceptance", "Acceptance Criteria", self.acceptance, 0),
        ]

        for field_name, label, items, _limit in _list_fields:
            if not items:
                continue
            if emphasis_set and field_name not in emphasis_set:
                # Compact: single line with semicolons
                compact = "; ".join(items[:3])
                if len(items) > 3:
                    compact += f" (+{len(items) - 3} more)"
                lines.append(f"**{label}:** {compact}")
                lines.append("")
            else:
                # Full detail
                lines.append(f"**{label}:**")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        if self.artifacts:
            lines.append("**Artifacts:**")
            for ref in self.artifacts:
                lines.append(f"- {ref.to_inline()}")
            lines.append("")

        if self.work_scope:
            if emphasis_set and "work_scope" not in emphasis_set:
                compact = ", ".join(self.work_scope[:5])
                if len(self.work_scope) > 5:
                    compact += f" (+{len(self.work_scope) - 5} more)"
                lines.append(f"**Work Scope:** {compact}")
            else:
                lines.append("**Work Scope:**")
                for item in self.work_scope:
                    lines.append(f"- {item}")
            lines.append("")

        if self.stage_hints:
            if emphasis_set and "stage_hints" not in emphasis_set:
                hint_count = len(self.stage_hints)
                lines.append(f"**Stage Hints:** {hint_count} hint(s) for downstream stages")
            else:
                lines.append("**Stage Hints:**")
                for stage, hint in self.stage_hints.items():
                    lines.append(f"- **{stage}:** {hint}")
            lines.append("")

        if self.quality_signals:
            if emphasis_set and "quality_signals" not in emphasis_set:
                sig_summary = ", ".join(
                    f"{k}={v}" for k, v in list(self.quality_signals.items())[:3]
                )
                lines.append(f"**Quality Signals:** {sig_summary}")
            else:
                lines.append("**Quality Signals:**")
                for key, value in self.quality_signals.items():
                    lines.append(f"- **{key}:** {value}")
            lines.append("")

        return "\n".join(lines)

    def apply_patch(self, patch: dict[str, Any]) -> Baton:
        """Apply a JSON merge patch to produce an updated baton.

        Supports partial updates: only fields present in the patch are changed.
        List fields are replaced entirely (not merged) per JSON merge patch semantics.
        None values remove the field (reset to default).

        Args:
            patch: Dictionary of field updates.

        Returns:
            New Baton instance with patch applied.
        """
        current = self.model_dump()

        for key, value in patch.items():
            if key not in current:
                continue
            if value is None:
                field_info = self.model_fields.get(key)
                if (
                    field_info
                    and field_info.default_factory
                    and callable(field_info.default_factory)
                ):
                    current[key] = field_info.default_factory()  # type: ignore[call-arg]
                elif field_info and field_info.default is not None:
                    current[key] = field_info.default
                else:
                    current[key] = ""
            else:
                current[key] = value

        return Baton.model_validate(current)

    def estimate_tokens(self) -> int:
        """Estimate token count of the rendered baton.

        Returns:
            Estimated token count.
        """
        from pixl.utils.tokens import estimate_tokens as _estimate

        rendered = self.to_prompt_section()
        return _estimate(rendered, "markdown")

    @classmethod
    def from_feature(cls, title: str, description: str) -> Baton:
        """Initialize a baton from feature metadata.

        Args:
            title: Feature title (becomes goal).
            description: Feature description (parsed for constraints/acceptance).

        Returns:
            Initial baton for a workflow session.
        """
        return cls(
            goal=title,
            current_state=["Workflow starting"],
            decision_log=[],
            open_questions=[],
            constraints=[],
            artifacts=[],
            work_scope=[],
            acceptance=[],
        )

    def to_json(self) -> str:
        """Serialize baton to compact JSON string."""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, data: str) -> Baton:
        """Deserialize baton from JSON string."""
        return cls.model_validate_json(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Baton:
        """Create baton from dictionary (e.g., session.baton)."""
        return cls.model_validate(data)


__all__ = [
    "ArtifactRef",
    "Baton",
]
