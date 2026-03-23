"""Unified context compiler for budget-aware prompt assembly.

Merges the capabilities of ContextCompiler and StructuredContextCompiler into
a single compiler that:

1. Includes baton context (goal, state, decisions, constraints)
2. Selects minimal artifact slices (summary > diff > excerpt > full)
3. Includes predecessor outputs from structured mode
4. Fills up to the model's token budget
5. Returns the assembled prompt plus a full audit trail

The baton is NOW rendered into prompts (unlike the old ContextCompiler),
making goal anchoring, decision history, and constraints visible to agents.

Assembly order:
1. Base prompt (from template resolver)
2. Baton context (via Baton.to_prompt_section())
3. Stage contract summary
4. Predecessor outputs (from session.structured_outputs)
5. Artifact handoff manifest (required artifact provenance + hashes)
6. Required artifacts (budget-aware layer selection)
7. Frozen artifacts (budget-aware layer selection)
8. Work-scope artifacts from baton (budget-aware)
9. Session state (if non-empty)
10. Output schema (if defined)
11. Envelope instructions (unified: <pixl_output> with baton_patch in payload)
12. Rejection feedback (appended by executor)
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from pixl.context.differ import ArtifactDiffer
from pixl.context.summarizer import ArtifactSummarizer
from pixl.models.baton import Baton
from pixl.models.context_slice import CompiledContext, ContextSlice
from pixl.prompts.schema_contract import load_json_schema, render_payload_contract

logger = logging.getLogger(__name__)

# Token budget targets per model tier
MODEL_BUDGETS: dict[str, int] = {
    # Haiku tier (fast, cheap — 200K context)
    "claude-haiku-4-5": 32_000,
    "haiku": 32_000,
    # Sonnet tier (execution — 200K context)
    "claude-sonnet-4-6": 64_000,
    "sonnet": 64_000,
    # Opus tier (strategic — 200K context)
    "claude-opus-4-6": 128_000,
    "opus": 128_000,
    # Codex tier (review — 128K context)
    "gpt-5.2-codex": 64_000,
    "codex": 64_000,
}

# Default budget if model not recognized
DEFAULT_BUDGET = 32_000


def _resolve_budget(model: str) -> int:
    """Resolve token budget for a model string.

    Args:
        model: Model identifier (may include provider prefix).

    Returns:
        Token budget target.
    """
    # Strip provider prefix (e.g., "anthropic/claude-sonnet-4-6" -> "claude-sonnet-4-6")
    model_name = model.split("/")[-1] if "/" in model else model

    # Exact match
    if model_name in MODEL_BUDGETS:
        return MODEL_BUDGETS[model_name]

    # Partial match (e.g., "haiku" in model name)
    model_lower = model_name.lower()
    for key, budget in MODEL_BUDGETS.items():
        if key in model_lower:
            return budget

    return DEFAULT_BUDGET


def _estimate_tokens(text: str) -> int:
    """Estimate token count using content-type-aware ratio.

    Args:
        text: Text to estimate.

    Returns:
        Estimated token count.
    """
    from pixl.utils.tokens import estimate_tokens

    return estimate_tokens(text, "markdown")


def _compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        path: File path.

    Returns:
        Hex digest string.
    """
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _extract_sections(content: str, section_names: list[str]) -> str | None:
    """Extract specific markdown sections by heading name.

    Finds sections matching any of the given names (case-insensitive),
    including their content up to the next heading of equal or higher level.

    Args:
        content: Full markdown content.
        section_names: List of section heading names to extract
                       (e.g. ["Tasks", "Testing Strategy"]).

    Returns:
        Concatenated section content, or None if no sections matched.
    """
    if not section_names:
        return None

    names_lower = {n.lower() for n in section_names}
    lines = content.splitlines()
    result_parts: list[str] = []
    capturing = False
    capture_level = 0

    for line in lines:
        # Check if this is a heading
        if line.startswith("#"):
            # Determine heading level
            level = 0
            for ch in line:
                if ch == "#":
                    level += 1
                else:
                    break
            heading_text = line.lstrip("#").strip().lower()

            # Check for pipe-separated aliases (e.g., "Tasks|Implementation Tasks")
            if heading_text in names_lower or any(
                heading_text == alias.lower() for name in section_names for alias in name.split("|")
            ):
                capturing = True
                capture_level = level
                result_parts.append(line)
            elif capturing and level <= capture_level:
                # Hit a same-or-higher-level heading — stop capturing
                capturing = False
            elif capturing:
                # Sub-heading within captured section
                result_parts.append(line)
        elif capturing:
            result_parts.append(line)

    if not result_parts:
        return None
    return "\n".join(result_parts)


def _include_artifact(
    artifact_path: Path,
    artifact_name: str,
    summarizer: ArtifactSummarizer,
    differ: ArtifactDiffer,
    frozen_artifacts: dict[str, str],
    reason: str,
    budget_remaining: int,
    force_summary: bool = False,
    prefer_diff: bool = False,
    priority: str = "standard",
    sections: list[str] | None = None,
    max_lines: int | None = None,
) -> tuple[ContextSlice, str] | None:
    """Include an artifact at the best layer for its priority level.

    Layer preference depends on priority:
    - critical: sections > full > excerpt > summary (maximize content)
    - standard: excerpt > summary > diff (balanced)
    - background: summary > diff (minimize tokens)

    Args:
        artifact_path: Full path to the artifact file.
        artifact_name: Artifact filename for identification.
        summarizer: ArtifactSummarizer for generating summaries.
        differ: ArtifactDiffer for generating diffs.
        frozen_artifacts: Map of frozen artifact paths to SHA256 hashes.
        reason: Why this is being included.
        budget_remaining: Tokens left in budget.
        force_summary: Always use summary layer.
        prefer_diff: Prefer diff over summary if available.
        priority: Inclusion priority: critical, standard, or background.
        sections: Specific markdown sections to extract (for section-aware excerpting).
        max_lines: Override default excerpt length.

    Returns:
        Tuple of (ContextSlice, formatted content) or None.
    """
    if not artifact_path.is_file():
        return None

    file_hash = _compute_file_hash(artifact_path)

    # For critical artifacts with sections specified, try section extraction first
    if priority == "critical" and sections:
        try:
            full_content = artifact_path.read_text(encoding="utf-8")
            extracted = _extract_sections(full_content, sections)
            if extracted:
                extracted_tokens = _estimate_tokens(extracted)
                if extracted_tokens <= budget_remaining:
                    sec_label = ", ".join(sections[:3])
                    content = f"## {artifact_name} (sections: {sec_label})\n\n{extracted}"
                    return (
                        ContextSlice(
                            artifact_id=artifact_name,
                            hash=file_hash[:16],
                            layer="excerpt",
                            reason=f"{reason} (section_extract)",
                            token_estimate=_estimate_tokens(content),
                            content=content,
                        ),
                        content,
                    )
        except OSError:
            pass

    # For critical artifacts, try full content first (maximize information)
    if priority == "critical" and not force_summary:
        try:
            full_content = artifact_path.read_text(encoding="utf-8")
            full_tokens = _estimate_tokens(full_content)
            if full_tokens <= budget_remaining:
                content = f"## {artifact_name} (full)\n\n{full_content}"
                return (
                    ContextSlice(
                        artifact_id=artifact_name,
                        hash=file_hash[:16],
                        layer="full",
                        reason=reason,
                        token_estimate=_estimate_tokens(content),
                        content=content,
                    ),
                    content,
                )
        except OSError:
            pass

    # Try summary first (cheapest) — default for standard/background
    if not prefer_diff or force_summary:
        summary = summarizer.get_summary_sync(artifact_path, file_hash)
        summary_tokens = _estimate_tokens(summary)
        if summary_tokens <= budget_remaining:
            content = f"## {artifact_name} (summary)\n\n{summary}"
            return (
                ContextSlice(
                    artifact_id=artifact_name,
                    hash=file_hash[:16],
                    layer="summary",
                    reason=reason,
                    token_estimate=_estimate_tokens(content),
                    content=content,
                ),
                content,
            )

    # Try diff if available
    frozen_hash = frozen_artifacts.get(artifact_name)
    if frozen_hash and frozen_hash != file_hash:
        cached_diff = differ.get_cached_diff(artifact_name, frozen_hash, file_hash)
        if cached_diff:
            diff_tokens = _estimate_tokens(cached_diff)
            if diff_tokens <= budget_remaining:
                content = f"## {artifact_name} (diff)\n\n```diff\n{cached_diff}\n```"
                return (
                    ContextSlice(
                        artifact_id=artifact_name,
                        hash=file_hash[:16],
                        layer="diff",
                        reason=reason,
                        token_estimate=_estimate_tokens(content),
                        content=content,
                    ),
                    content,
                )

    # Try excerpt (proportional: min(100, half of file))
    try:
        full_content = artifact_path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = full_content.splitlines()
    # Use max_lines override if provided, otherwise proportional sizing
    excerpt_size = max_lines if max_lines else min(100, max(50, len(lines) // 2))
    if len(lines) > excerpt_size:
        excerpt = "\n".join(lines[:excerpt_size]) + f"\n\n... (truncated, {len(lines)} total lines)"
        excerpt_tokens = _estimate_tokens(excerpt)
        if excerpt_tokens <= budget_remaining:
            content = f"## {artifact_name} (excerpt, lines 1-{excerpt_size})\n\n{excerpt}"
            return (
                ContextSlice(
                    artifact_id=artifact_name,
                    hash=file_hash[:16],
                    layer="excerpt",
                    excerpt_range=(1, excerpt_size),
                    reason=reason,
                    token_estimate=_estimate_tokens(content),
                    content=content,
                ),
                content,
            )

    # Full content as last resort
    full_tokens = _estimate_tokens(full_content)
    if full_tokens <= budget_remaining:
        content = f"## {artifact_name} (full)\n\n{full_content}"
        return (
            ContextSlice(
                artifact_id=artifact_name,
                hash=file_hash[:16],
                layer="full",
                reason=reason,
                token_estimate=_estimate_tokens(content),
                content=content,
            ),
            content,
        )

    # Too large even for full - fall back to summary
    summary = summarizer.get_summary_sync(artifact_path, file_hash)
    content = f"## {artifact_name} (summary, full too large for budget)\n\n{summary}"
    return (
        ContextSlice(
            artifact_id=artifact_name,
            hash=file_hash[:16],
            layer="summary",
            reason=f"{reason} (budget_constrained)",
            token_estimate=_estimate_tokens(content),
            content=content,
        ),
        content,
    )


class UnifiedContextCompiler:
    """Assembles minimal, auditable prompts with baton context integration.

    The unified compiler merges the capabilities of both ContextCompiler and
    StructuredContextCompiler, providing:

    - Baton context rendered into prompts (goal, state, decisions, constraints)
    - Predecessor summaries from structured outputs
    - Budget-aware artifact selection (summary > diff > excerpt > full)
    - Work-scope tracking from baton
    - Unified envelope instructions with baton_patch in payload

    Assembly order:
    1. Base prompt (always included)
    2. Baton context (goal, state, decisions, constraints, work_scope)
    3. Stage contract summary
    4. Predecessor outputs
    5. Required artifacts
    6. Frozen artifacts
    7. Work-scope artifacts
    8. Session state
    9. Output schema (if defined)
    10. Envelope instructions
    """

    def __init__(
        self,
        artifacts_dir: Path,
        summarizer: ArtifactSummarizer,
        differ: ArtifactDiffer,
        frozen_artifacts: dict[str, str] | None = None,
    ):
        """Initialize the unified context compiler.

        Args:
            artifacts_dir: Directory containing workflow artifacts.
            summarizer: Artifact summarizer for generating summaries.
            differ: Artifact differ for generating diffs.
            frozen_artifacts: Map of frozen artifact paths to SHA256 hashes.
        """
        self.artifacts_dir = artifacts_dir
        self.summarizer = summarizer
        self.differ = differ
        self.frozen_artifacts = frozen_artifacts or {}

    def compile(
        self,
        base_prompt: str,
        model: str,
        baton: Baton,
        predecessor_outputs: dict[str, dict[str, Any]] | None = None,
        stage_config: dict[str, Any] | None = None,
        session_state: dict[str, Any] | None = None,
        output_schema_path: str | None = None,
        stage_id: str | None = None,
        context_needs: Any | None = None,
        max_budget_override: int | None = None,
        artifact_handoff_manifest: list[dict[str, Any]] | None = None,
    ) -> CompiledContext:
        """Compile a context-optimized prompt with baton integration.

        Args:
            base_prompt: Base prompt from template resolver.
            model: Model identifier for budget resolution.
            baton: Current baton state (will be rendered into prompt).
            predecessor_outputs: Map of node_id -> StageOutput dict from predecessors.
            stage_config: Stage configuration dict from workflow YAML.
            session_state: Small executor metadata dict.
            output_schema_path: Path to JSON Schema for this stage's output.
            stage_id: Current stage ID (for stage hint rendering).
            context_needs: Optional ContextNeeds declaration from workflow YAML.
            max_budget_override: Optional hard cap on token budget (takes min
                with model default). Used to enforce TaskConfig.max_input_tokens.
            artifact_handoff_manifest: Optional required-artifact manifest
                generated before task execution.

        Returns:
            CompiledContext with assembled prompt and audit trail.
        """
        stage_config = stage_config or {}
        predecessor_outputs = predecessor_outputs or {}
        budget = _resolve_budget(model)
        if max_budget_override is not None:
            budget = min(budget, max_budget_override)
        slices: list[ContextSlice] = []

        prompt_parts: list[str] = []
        used_tokens = 0

        # Import here to avoid circular imports
        artifact_needs_map: dict[str, Any] = {}  # name -> ArtifactNeed
        predecessor_needs_map: dict[str, Any] = {}  # stage_id -> PredecessorNeed
        baton_emphasis: list[str] = []
        if context_needs is not None:
            for an in getattr(context_needs, "artifacts", []):
                artifact_needs_map[an.name] = an
            for pn in getattr(context_needs, "predecessors", []):
                predecessor_needs_map[pn.stage_id] = pn
            baton_emphasis = getattr(context_needs, "baton_emphasis", [])

        # 1. Base prompt (always included)
        prompt_parts.append(base_prompt)
        used_tokens += _estimate_tokens(base_prompt)

        # 1b. Early envelope reminder (reduces validation retries)
        early_reminder = (
            "IMPORTANT: When you finish your work, your FINAL response MUST include "
            "a `<pixl_output>` JSON envelope. Do NOT omit it. See full format below."
        )
        prompt_parts.append(early_reminder)
        used_tokens += _estimate_tokens(early_reminder)

        # 2. Baton context (with optional emphasis from context_needs)
        baton_section = baton.to_prompt_section(emphasis=baton_emphasis or None)
        baton_tokens = _estimate_tokens(baton_section)
        if used_tokens + baton_tokens <= budget:
            prompt_parts.append(baton_section)
            used_tokens += baton_tokens

        # 2b. Stage hint (if baton has a targeted hint for this stage)
        if stage_id and baton.stage_hints.get(stage_id):
            hint = baton.stage_hints[stage_id]
            hint_section = f"> **Stage Hint (from prior stage):** {hint}"
            hint_tokens = _estimate_tokens(hint_section)
            if used_tokens + hint_tokens <= budget:
                prompt_parts.append(hint_section)
                used_tokens += hint_tokens

        # 3. Stage contract summary
        contract_summary = self._build_contract_summary(stage_config)
        if contract_summary:
            contract_tokens = _estimate_tokens(contract_summary)
            if used_tokens + contract_tokens <= budget:
                prompt_parts.append(contract_summary)
                used_tokens += contract_tokens

        # 4. Predecessor outputs (with context_needs-aware detail levels)
        if predecessor_outputs:
            pred_section = self._build_predecessor_section(
                predecessor_outputs, predecessor_needs_map=predecessor_needs_map
            )
            pred_tokens = _estimate_tokens(pred_section)
            if used_tokens + pred_tokens <= budget:
                prompt_parts.append(pred_section)
                used_tokens += pred_tokens

        # 4b. Explicit required-artifact handoff manifest
        if artifact_handoff_manifest:
            handoff_section = self._build_artifact_handoff_section(artifact_handoff_manifest)
            handoff_tokens = _estimate_tokens(handoff_section)
            if used_tokens + handoff_tokens <= budget:
                prompt_parts.append(handoff_section)
                used_tokens += handoff_tokens

        # NOTE: Progress memory section removed — the baton (step 2) already
        # provides the same content. Progress artifacts are still written by
        # graph_executor._persist_progress_artifact() for session recovery/debugging
        # but no longer injected into prompts (eliminates ~300-500 token duplication).

        # 5-7. Artifacts: two-pass priority-aware assembly
        required = stage_config.get("required_artifacts", [])
        all_artifact_entries: list[tuple[str, str, dict[str, Any]]] = []  # (name, reason, kwargs)

        # Required artifacts
        for artifact_name in required:
            need = artifact_needs_map.get(artifact_name)
            kwargs: dict[str, Any] = {}
            if need:
                kwargs["priority"] = need.priority
                kwargs["sections"] = need.sections
                kwargs["max_lines"] = need.max_lines
            all_artifact_entries.append((artifact_name, "required_artifact", kwargs))

        # Frozen artifacts (not already in required)
        for frozen_path, _frozen_hash in self.frozen_artifacts.items():
            if frozen_path in required:
                continue
            need = artifact_needs_map.get(frozen_path)
            kwargs = {"force_summary": True}
            if need:
                kwargs["priority"] = need.priority
                kwargs["sections"] = need.sections
                kwargs["max_lines"] = need.max_lines
                # Don't force summary for critical frozen artifacts
                if need.priority == "critical":
                    kwargs["force_summary"] = False
            all_artifact_entries.append((frozen_path, "frozen_artifact", kwargs))

        # Work-scope artifacts from baton
        already_listed = {e[0] for e in all_artifact_entries}
        for scope_item in baton.work_scope:
            if scope_item in already_listed:
                continue
            scope_path = self.artifacts_dir / scope_item
            if not scope_path.exists():
                continue
            need = artifact_needs_map.get(scope_item)
            kwargs = {"prefer_diff": True}
            if need:
                kwargs["priority"] = need.priority
                kwargs["sections"] = need.sections
                kwargs["max_lines"] = need.max_lines
            all_artifact_entries.append((scope_item, "work_scope", kwargs))

        # Context-needs declared artifacts not yet listed
        for art_name, need in artifact_needs_map.items():
            if art_name in already_listed and art_name not in {e[0] for e in all_artifact_entries}:
                continue
            if any(e[0] == art_name for e in all_artifact_entries):
                continue
            all_artifact_entries.append(
                (
                    art_name,
                    "context_needs",
                    {
                        "priority": need.priority,
                        "sections": need.sections,
                        "max_lines": need.max_lines,
                    },
                )
            )

        # Two-pass: critical first, then standard/background
        for pass_priorities in [["critical"], ["standard", "background"]]:
            for artifact_name, reason, kwargs in all_artifact_entries:
                if used_tokens >= budget:
                    break
                entry_priority = kwargs.get("priority", "standard")
                if entry_priority not in pass_priorities:
                    continue
                # Skip if already included
                if artifact_name in {s.artifact_id for s in slices}:
                    continue
                artifact_path = self.artifacts_dir / artifact_name
                slice_result = _include_artifact(
                    artifact_path=artifact_path,
                    artifact_name=artifact_name,
                    summarizer=self.summarizer,
                    differ=self.differ,
                    frozen_artifacts=self.frozen_artifacts,
                    reason=reason,
                    budget_remaining=budget - used_tokens,
                    **{k: v for k, v in kwargs.items() if v is not None},
                )
                if slice_result:
                    cs, content = slice_result
                    slices.append(cs)
                    prompt_parts.append(content)
                    used_tokens += cs.token_estimate

        # 8. Session state
        if session_state:
            state_section = self._build_session_state_section(session_state)
            state_tokens = _estimate_tokens(state_section)
            if used_tokens + state_tokens <= budget:
                prompt_parts.append(state_section)
                used_tokens += state_tokens

        # 9. Output schema instructions
        if output_schema_path:
            # Always inject compact schema-derived payload contract.
            schema_contract = self._build_schema_contract_section(output_schema_path)
            if schema_contract:
                prompt_parts.append(schema_contract)
                used_tokens += _estimate_tokens(schema_contract)

            # Include full schema only when budget allows.
            schema_reference = self._build_schema_reference_section(output_schema_path)
            if schema_reference:
                schema_tokens = _estimate_tokens(schema_reference)
                if used_tokens + schema_tokens <= budget:
                    prompt_parts.append(schema_reference)
                    used_tokens += schema_tokens

        # 10. Envelope instructions (always included)
        envelope_instr = self._build_envelope_instructions(stage_id=stage_id)
        instr_tokens = _estimate_tokens(envelope_instr)
        prompt_parts.append(envelope_instr)
        used_tokens += instr_tokens

        prompt_text = "\n\n".join(prompt_parts)

        return CompiledContext(
            baton=baton,
            stage_contract_summary=contract_summary,
            slices=slices,
            total_tokens=used_tokens,
            budget_tokens=budget,
            prompt_text=prompt_text,
        )

    @staticmethod
    def _build_predecessor_section(
        predecessor_outputs: dict[str, dict[str, Any]],
        predecessor_needs_map: dict[str, Any] | None = None,
    ) -> str:
        """Build context section from predecessor structured outputs.

        Args:
            predecessor_outputs: Map of node_id -> StageOutput dict.
            predecessor_needs_map: Map of stage_id -> PredecessorNeed for
                controlling detail level. When a PredecessorNeed has
                include="full_payload", the full payload dict is rendered.
        """
        needs_map = predecessor_needs_map or {}
        lines = ["## Prior Stage Outputs", ""]

        for node_id, output_dict in predecessor_outputs.items():
            lines.append(f"### {node_id}")

            status = output_dict.get("status", "unknown")
            lines.append(f"**Status:** {status}")

            summary = output_dict.get("summary", [])
            if summary:
                lines.append("**Summary:**")
                for bullet in summary[:10]:
                    lines.append(f"- {bullet}")

            artifacts = output_dict.get("artifacts_written", [])
            if artifacts:
                lines.append("**Artifacts produced:**")
                for art in artifacts:
                    path = art.get("path", "unknown")
                    purpose = art.get("purpose", "")
                    lines.append(f"- `{path}`: {purpose}")

            # Enhanced: include payload details based on PredecessorNeed
            need = needs_map.get(node_id)
            payload = output_dict.get("payload", {})
            if need and payload:
                include_level = getattr(need, "include", "summary")
                if include_level == "full_payload":
                    lines.append("**Payload:**")
                    lines.append("```yaml")
                    import yaml

                    display_payload = {k: v for k, v in payload.items() if k != "baton_patch"}
                    if display_payload:
                        lines.append(
                            yaml.dump(
                                display_payload,
                                default_flow_style=False,
                                sort_keys=False,
                                allow_unicode=True,
                            ).rstrip()
                        )
                    lines.append("```")
                elif include_level == "specific_fields":
                    fields = getattr(need, "fields", None) or []
                    if fields:
                        lines.append("**Selected payload fields:**")
                        for field in fields:
                            if field in payload and field != "baton_patch":
                                val = payload[field]
                                if isinstance(val, (dict, list)):
                                    lines.append(f"- **{field}:** {json.dumps(val, indent=2)}")
                                else:
                                    lines.append(f"- **{field}:** {val}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _build_session_state_section(session_state: dict[str, Any]) -> str:
        """Build session state section."""
        lines = ["## Session State", ""]
        for key, value in session_state.items():
            if isinstance(value, (list, dict)):
                lines.append(f"**{key}:** {json.dumps(value, indent=2)}")
            else:
                lines.append(f"**{key}:** {value}")
        return "\n".join(lines)

    @staticmethod
    def _build_artifact_handoff_section(manifest: list[dict[str, Any]]) -> str:
        """Build explicit handoff metadata for required artifacts."""
        lines = ["## Artifact Handoff Manifest", ""]
        for entry in manifest:
            path = str(entry.get("path", ""))
            exists = "yes" if bool(entry.get("exists")) else "no"
            sha256 = str(entry.get("sha256") or "missing")
            version = str(entry.get("version") or "unknown")
            producer = str(entry.get("producer_stage") or "unknown")
            lines.append(
                f"- `{path}` | exists={exists} | sha256={sha256} | "
                f"version={version} | producer_stage={producer}"
            )
        return "\n".join(lines)

    def _build_schema_contract_section(self, schema_path: str) -> str | None:
        """Build compact payload contract section from output schema."""
        resolved = self.artifacts_dir / schema_path
        if not resolved.exists():
            # Try as absolute or project-relative
            resolved = Path(schema_path)
            if not resolved.exists():
                return None

        schema_data = load_json_schema(resolved)
        if schema_data is None:
            return None

        return render_payload_contract(
            schema_data,
            heading="## Output Schema Contract",
        )

    def _build_schema_reference_section(self, schema_path: str) -> str | None:
        """Build full JSON schema reference section (budget-permitting)."""
        resolved = self.artifacts_dir / schema_path
        if not resolved.exists():
            resolved = Path(schema_path)
            if not resolved.exists():
                return None

        schema_data = load_json_schema(resolved)
        if schema_data is None:
            return None

        lines = [
            "## Output Schema Reference",
            "",
            "Full JSON Schema for `payload`:",
            "",
            "```json",
            json.dumps(schema_data, indent=2),
            "```",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_envelope_instructions(stage_id: str | None = None) -> str:
        """Build instructions for producing structured output envelopes with baton_patch.

        Args:
            stage_id: Current stage ID to pre-fill in the example.
        """
        sid = stage_id or "<stage-id>"
        return (
            "## Structured Output Instructions\n\n"
            "When done, wrap your result in `<pixl_output>` tags with valid JSON:\n\n"
            "```\n"
            "<pixl_output>\n"
            f'{{"schema_version":"1.0","stage_id":"{sid}","status":"ok",'
            '"summary":["what you did"],"artifacts_written":[],'
            '"payload":{"baton_patch":{"current_state":["..."]}}}\n'
            "</pixl_output>\n"
            "```\n\n"
            "Checklist:\n"
            "1. `<pixl_output>` tags MUST appear exactly once, with valid JSON inside\n"
            "2. `summary`: 1-10 concise bullets; `artifacts_written`: files you created/modified "
            "(save via `pixl artifact put` first)\n"
            '3. On error: set `status` to `"error"` and add an `error` field\n\n'
            "Optional in `payload`:\n"
            "- `baton_patch`: update workflow baton — `current_state` (3-8 bullets), "
            "`decision_log`, `work_scope`, `constraints`, `open_questions` "
            "(only include fields you changed; omit if no progress to report)\n"
            '- `included_sources`: `[{"artifact_id":"...","reason":"..."}]`\n'
            '- `next`: `{"recommended_stage":"...","inputs_needed":[...]}`'
        )

    @staticmethod
    def _build_contract_summary(stage_config: dict[str, Any]) -> str:
        """Build a summary of the stage contract.

        Args:
            stage_config: Stage configuration dict.

        Returns:
            Markdown section summarizing what this stage must produce.
        """
        contract = stage_config.get("contract")
        if not contract:
            outputs = stage_config.get("outputs", [])
            if outputs:
                lines = ["## Stage Contract", ""]
                lines.append("**Must produce:**")
                for o in outputs:
                    lines.append(f"- {o}")
                return "\n".join(lines)
            return ""

        lines = ["## Stage Contract", ""]

        if hasattr(contract, "must_write"):
            must_write = contract.must_write
            must_include = contract.must_include_sections
            detect_stubs = contract.detect_stubs
        else:
            must_write = contract.get("must_write", [])
            must_include = contract.get("must_include_sections", {})
            detect_stubs = contract.get("detect_stubs", False)

        if must_write:
            lines.append("**Must write:**")
            for f in must_write:
                lines.append(f"- `{f}`")
            lines.append("")

        if must_include:
            lines.append("**Required sections:**")
            for file, sections in must_include.items():
                for s in sections:
                    lines.append(f"- `{file}`: {s}")
            lines.append("")

        if detect_stubs:
            lines.append("**No stubs/TODOs allowed in output**")
            lines.append("")

        return "\n".join(lines)


__all__ = [
    "UnifiedContextCompiler",
    "MODEL_BUDGETS",
    "DEFAULT_BUDGET",
    "_resolve_budget",
    "_estimate_tokens",
    "_compute_file_hash",
    "_extract_sections",
    "_include_artifact",
]
