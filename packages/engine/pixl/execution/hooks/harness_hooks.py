"""Quality gate hooks for iterative workflows.

score-gate: Reads quality_signals scores against a configurable threshold.
findings-gate: Reads quality_signals open_findings count — passes when zero.

Both hooks trigger LoopConstraint back-edges on failure.
"""

from __future__ import annotations

from typing import Any

from pixl.execution.hooks import HookContext, HookResult, register_hook

_DEFAULT_THRESHOLD = 7
_DEFAULT_CRITERIA = ["design_quality", "originality", "craft", "functionality"]


@register_hook("score-gate")
def score_gate_hook(ctx: HookContext) -> HookResult:
    """Evaluate quality signals against a threshold to gate workflow progress."""
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

    # --- Gate decision ---
    if not failed_criteria:
        return HookResult(
            success=True,
            data={**scores, "iteration": iteration, "passed": True},
        )

    # Failure path — forward critique to the generator via stage_hints
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
        data={**scores, "iteration": iteration, "failed_criteria": failed_criteria},
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
