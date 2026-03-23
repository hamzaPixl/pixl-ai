"""Review stage validation for workflow execution.

Extracted from graph_executor.py — handles review stage detection,
structured output validation, and safe default generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pixl.models.workflow import WorkflowSnapshot


def normalize_review_recommendation(recommendation: str | None) -> str | None:
    """Normalize review recommendation variants to schema enum values.

    Canonical enum:
    - approve
    - request_changes
    - reject
    """
    if recommendation is None:
        return None

    token = recommendation.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "approve": "approve",
        "approved": "approve",
        "pass": "approve",
        "passed": "approve",
        "ok": "approve",
        "request_changes": "request_changes",
        "request_change": "request_changes",
        "changes_requested": "request_changes",
        "needs_work": "request_changes",
        "needs_changes": "request_changes",
        "reject": "reject",
        "rejected": "reject",
        "fail": "reject",
        "failed": "reject",
    }
    return aliases.get(token, recommendation)


def normalize_review_payload(payload: dict | None) -> bool:
    """Normalize payload.recommendation in-place when possible.

    Returns:
        True if payload was modified.
    """
    if not isinstance(payload, dict):
        return False
    recommendation = payload.get("recommendation")
    if not isinstance(recommendation, str):
        return False
    normalized = normalize_review_recommendation(recommendation)
    if normalized != recommendation:
        payload["recommendation"] = normalized
        return True
    return False


def is_review_stage(node_id: str, snapshot: WorkflowSnapshot) -> bool:
    """Check if a node is a review stage.

    Review stages are expected to produce structured output with
    a recommendation field.

    Args:
        node_id: Node ID to check
        snapshot: Workflow snapshot for node lookups

    Returns:
        True if this is a review stage
    """
    review_stages = [
        "code-review",
        "plan-review",
        "design-review",
        "automated-checks",
        "review",
    ]
    # Check by stage ID prefix or exact match
    for review_id in review_stages:
        if node_id == review_id or node_id.endswith(f"-{review_id}"):
            return True

    # Also check agent type
    node = snapshot.graph.nodes.get(node_id)
    if node and node.task_config:
        agent = node.task_config.agent
        if agent in ["code-reviewer", "plan-reviewer", "reviewer"]:
            return True

    return False


def validate_review_structured_output(
    node_id: str,
    structured_output: dict | None,
    snapshot: WorkflowSnapshot,
) -> tuple[bool, str]:
    """Validate that review stages produce required recommendation field.

    Args:
        node_id: Node ID
        structured_output: Extracted structured output payload
        snapshot: Workflow snapshot for review stage detection

    Returns:
        (is_valid, error_message)
    """
    if not is_review_stage(node_id, snapshot):
        return True, ""

    if not structured_output:
        # Safe default: require changes if we can't parse the review
        return False, "Review stage must produce structured output with recommendation"

    payload = structured_output.get("payload", {})
    normalize_review_payload(payload)
    recommendation = payload.get("recommendation")

    if not recommendation:
        return False, "Review payload missing 'recommendation' field"

    valid_recommendations = ["approve", "request_changes", "reject"]
    if recommendation not in valid_recommendations:
        return (
            False,
            f"Invalid recommendation: {recommendation}. Must be one of {valid_recommendations}",
        )

    return True, ""


def get_default_review_output() -> dict:
    """Get default structured output for review stages when extraction fails.

    Returns:
        Default output with request_changes recommendation (safe default)
    """
    return {
        "status": "ok",
        "summary": (
            "Review completed (structured output extraction failed - defaulting to request_changes)"
        ),
        "payload": {
            "recommendation": "request_changes",
            "issues": [
                {
                    "severity": "critical",
                    "message": "Structured output could not be parsed - manual review required",
                }
            ],
        },
    }
