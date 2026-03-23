"""Sync workflow materialization hooks.

Reads the structured scan-main payload and applies feature status updates:
- mark_done: updates feature status to done with PR URL audit note
- already_done: skipped (no-op)
- no_pr: skipped (no-op)

Emits a sync_completed event after applying all changes.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from pixl.execution.hooks import HookContext, HookResult, register_hook
from pixl.storage.db.connection import PixlDB


def _get_scan_payload(ctx: HookContext) -> dict[str, Any]:
    """Extract the structured payload from the scan-main stage output."""
    source_node_id = str(ctx.params.get("source_node_id", "scan-main"))
    structured = ctx.session.structured_outputs.get(source_node_id, {})
    if not isinstance(structured, dict):
        return {}
    payload = structured.get("payload", {})
    return payload if isinstance(payload, dict) else {}


@register_hook("materialize-sync-results")
def materialize_sync_results_hook(ctx: HookContext) -> HookResult:
    """Apply sync scan results: mark correlated features as done."""
    db = PixlDB(ctx.project_root)
    db.initialize()

    payload = _get_scan_payload(ctx)
    feature_actions = payload.get("feature_actions", [])
    if not isinstance(feature_actions, list):
        return HookResult(success=False, error="Missing or invalid feature_actions in scan payload")

    marked_done: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for action_item in feature_actions:
        if not isinstance(action_item, dict):
            continue

        feature_id = str(action_item.get("feature_id", "")).strip()
        action = str(action_item.get("action", "")).strip()

        if not feature_id or not action:
            continue

        # Only process mark_done actions
        if action != "mark_done":
            skipped.append(feature_id)
            continue

        feature = db.backlog.get_feature(feature_id)
        if feature is None:
            errors.append(f"Feature not found: {feature_id}")
            continue

        current_status = str(feature.get("status", ""))
        if current_status == "done":
            skipped.append(feature_id)
            continue

        pr_url = action_item.get("pr_url", "")
        pr_number = action_item.get("pr_number", "")
        note_parts = ["Marked done by sync workflow"]
        if pr_url:
            note_parts.append(f"PR: {pr_url}")
        elif pr_number:
            note_parts.append(f"PR #{pr_number}")

        db.backlog.update_feature_status(
            feature_id,
            status="done",
            note=" | ".join(note_parts),
            trigger="sync_workflow",
            trigger_id=ctx.session.id,
        )
        marked_done.append(feature_id)

    with contextlib.suppress(Exception):
        db.events.emit(
            event_type="sync_completed",
            session_id=ctx.session.id,
            entity_type="feature",
            entity_id=ctx.feature_id,
            payload={
                "marked_done": marked_done,
                "skipped": skipped,
                "errors": errors,
                "completed_at": datetime.now().isoformat(),
            },
        )

    return HookResult(
        success=True,
        data={
            "marked_done": marked_done,
            "skipped": skipped,
            "errors": errors,
            "total_actions": len(feature_actions),
        },
    )
