"""Quality gate hooks for iterative workflows.

score-gate: Reads quality_signals scores against a configurable threshold.
            Includes stagnation detection — early stop when scores plateau.
findings-gate: Reads quality_signals open_findings count — passes when zero.

Both hooks trigger LoopConstraint back-edges on failure.
"""

from __future__ import annotations

import logging
from typing import Any

from pixl.execution.hooks import HookContext, HookResult, register_hook

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 7
_DEFAULT_CRITERIA = ["design_quality", "originality", "craft", "functionality"]
_STAGNATION_WINDOW = 2  # consecutive iterations with no meaningful improvement
_STAGNATION_MIN_DELTA = 1.0  # minimum total score improvement to not be stagnant


def _detect_stagnation(
    score_history: list[dict[str, Any]],
    criteria: list[str],
    window: int = _STAGNATION_WINDOW,
    min_delta: float = _STAGNATION_MIN_DELTA,
) -> tuple[bool, str]:
    """Detect score stagnation across recent iterations.

    Returns (is_stagnant, reason).
    """
    if len(score_history) < window + 1:
        return False, ""

    recent = score_history[-(window + 1) :]
    baseline = recent[0]
    baseline_total = sum(baseline.get(c, 0) for c in criteria)

    for entry in recent[1:]:
        entry_total = sum(entry.get(c, 0) for c in criteria)
        delta = entry_total - baseline_total
        if delta >= min_delta:
            return False, ""

    current_total = sum(recent[-1].get(c, 0) for c in criteria)
    return True, (
        f"Scores stagnant for {window} iterations "
        f"(total={current_total}, delta<{min_delta}). "
        f"Further iterations unlikely to improve without a different approach."
    )


def _detect_escalation(quality_signals: dict[str, Any]) -> tuple[bool, str]:
    """Check if the generator reported being stuck."""
    escalation = quality_signals.get("escalation")
    stuck_issues = quality_signals.get("stuck_issues", [])

    if escalation and isinstance(escalation, str) and escalation.strip():
        return True, f"Generator escalated: {escalation[:200]}"
    if stuck_issues and isinstance(stuck_issues, list) and len(stuck_issues) > 0:
        issues = ", ".join(str(s) for s in stuck_issues[:3])
        return True, f"Generator stuck on: {issues}"
    return False, ""


@register_hook("score-gate")
def score_gate_hook(ctx: HookContext) -> HookResult:
    """Evaluate quality signals against a threshold to gate workflow progress.

    Includes stagnation detection and generator escalation handling.
    """
    threshold: int = ctx.params.get("threshold", _DEFAULT_THRESHOLD)
    criteria: list[str] = ctx.params.get("criteria", _DEFAULT_CRITERIA)

    # --- Validate baton presence ---
    baton: dict[str, Any] | None = ctx.session.baton
    if baton is None:
        return HookResult(success=False, error="Baton is not set on the session")

    quality_signals: dict[str, Any] = baton.get("quality_signals", {})
    if not isinstance(quality_signals, dict) or not quality_signals:
        return HookResult(
            success=False,
            error="No quality_signals found in the baton",
        )

    # --- Evaluate each criterion ---
    scores: dict[str, int] = {}
    failed_criteria: list[str] = []

    for criterion in criteria:
        score = quality_signals.get(criterion, 0)
        score = int(score) if isinstance(score, (int, float)) else 0
        scores[criterion] = score
        if score < threshold:
            failed_criteria.append(criterion)

    iteration: int = int(quality_signals.get("iteration", 0))
    critique_summary: str = str(quality_signals.get("critique_summary", ""))

    # --- Track score history ---
    score_history: list[dict[str, Any]] = quality_signals.get("score_history", [])
    if not isinstance(score_history, list):
        score_history = []
    current_snapshot = {c: scores.get(c, 0) for c in criteria}
    current_snapshot["iteration"] = iteration
    score_history.append(current_snapshot)
    quality_signals["score_history"] = score_history

    # --- Check for generator escalation (stuck issues) ---
    is_escalated, escalation_reason = _detect_escalation(quality_signals)
    if is_escalated:
        logger.warning(
            "Generator escalation detected at iteration %d: %s", iteration, escalation_reason
        )
        return HookResult(
            success=False,
            error=f"ESCALATION: {escalation_reason}",
            data={
                **scores,
                "iteration": iteration,
                "failed_criteria": failed_criteria,
                "escalated": True,
                "escalation_reason": escalation_reason,
                "action": "pause_for_human",
            },
        )

    # --- Gate decision: all pass ---
    if not failed_criteria:
        return HookResult(
            success=True,
            data={
                **scores,
                "iteration": iteration,
                "passed": True,
                "score_history": score_history,
            },
        )

    # --- Stagnation detection ---
    is_stagnant, stagnation_reason = _detect_stagnation(score_history, criteria)
    if is_stagnant:
        logger.warning(
            "Score stagnation detected at iteration %d: %s", iteration, stagnation_reason
        )
        # Inject stagnation diagnostic into stage_hints
        stagnation_hint = (
            f"STAGNATION DETECTED: {stagnation_reason}\n\n"
            f"Do NOT continue with the same approach. You must either:\n"
            f"1. Fundamentally change your approach to the failing criteria\n"
            f"2. Escalate to the user with what you tried and why it's not working\n\n"
            f"Score history: {score_history}"
        )
        stage_hints = baton.get("stage_hints")
        if isinstance(stage_hints, dict):
            stage_hints["generate"] = stagnation_hint
        else:
            baton["stage_hints"] = {"generate": stagnation_hint}

        failed_details = ", ".join(f"{c}={scores[c]}" for c in failed_criteria)
        return HookResult(
            success=False,
            error=f"STAGNATION: {stagnation_reason} Failing: {failed_details}",
            data={
                **scores,
                "iteration": iteration,
                "failed_criteria": failed_criteria,
                "stagnant": True,
                "stagnation_reason": stagnation_reason,
                "score_history": score_history,
                "action": "change_approach_or_escalate",
            },
        )

    # --- Normal failure path — forward critique to generator ---
    if critique_summary:
        stage_hints = baton.get("stage_hints")
        if isinstance(stage_hints, dict):
            stage_hints["generate"] = critique_summary
        else:
            baton["stage_hints"] = {"generate": critique_summary}

    failed_details = ", ".join(f"{c}={scores[c]}" for c in failed_criteria)
    return HookResult(
        success=False,
        error=f"Scores below threshold ({threshold}): {failed_details}",
        data={
            **scores,
            "iteration": iteration,
            "failed_criteria": failed_criteria,
            "score_history": score_history,
        },
    )


@register_hook("findings-gate")
def findings_gate_hook(ctx: HookContext) -> HookResult:
    """Pass when open findings count reaches zero.

    Used by review and security-audit workflows to loop until all
    actionable findings are resolved.

    Params:
        target_stage: Stage to forward findings summary to (default: "fix").
        severity_threshold: Max severity that blocks (default: "P1").
            "P0" = only P0 blocks, "P1" = P0+P1 block, "P2" = P0+P1+P2 block.
    """
    target_stage: str = ctx.params.get("target_stage", "fix")
    severity_threshold: str = ctx.params.get("severity_threshold", "P1")

    baton: dict[str, Any] | None = ctx.session.baton
    if baton is None:
        return HookResult(success=False, error="Baton is not set on the session")

    quality_signals: dict[str, Any] = baton.get("quality_signals", {})
    if not isinstance(quality_signals, dict):
        quality_signals = {}

    open_findings: int = int(quality_signals.get("open_findings", 0))
    max_severity: str = str(quality_signals.get("max_severity", "none"))

    # Determine which severities block
    severity_order = ["P0", "P1", "P2", "P3"]
    threshold_idx = (
        severity_order.index(severity_threshold) if severity_threshold in severity_order else 1
    )
    blocking_severities = set(severity_order[: threshold_idx + 1])

    # Pass if no open findings or max severity is below threshold
    if open_findings == 0 or (max_severity != "none" and max_severity not in blocking_severities):
        return HookResult(
            success=True,
            data={"open_findings": open_findings, "max_severity": max_severity, "passed": True},
        )

    # Failure — forward findings summary to the target stage
    findings_summary: str = str(quality_signals.get("findings_summary", ""))
    if findings_summary:
        stage_hints = baton.get("stage_hints")
        if isinstance(stage_hints, dict):
            stage_hints[target_stage] = findings_summary
        else:
            baton["stage_hints"] = {target_stage: findings_summary}

    return HookResult(
        success=False,
        error=f"{open_findings} open finding(s), max severity: {max_severity}",
        data={"open_findings": open_findings, "max_severity": max_severity},
    )
