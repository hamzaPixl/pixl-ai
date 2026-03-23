"""Replan workflow triage materialization hooks.

Reads the structured triage payload and applies decisions deterministically:
- mark_done: updates feature status to done
- defer: updates feature status to deferred with note
- remove: removes feature (only if no active sessions, else falls back to defer)
- reprioritize: updates feature priority with note
- new_features: creates new features from gap analysis suggestions

Emits a triage_applied event after applying all changes.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from pixl.execution.hooks import HookContext, HookResult, register_hook
from pixl.storage.db.connection import PixlDB


def _get_triage_payload(ctx: HookContext) -> dict[str, Any]:
    """Extract the structured payload from the triage stage output."""
    source_node_id = str(ctx.params.get("source_node_id", "triage"))
    structured = ctx.session.structured_outputs.get(source_node_id, {})
    if not isinstance(structured, dict):
        return {}
    payload = structured.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def _has_active_sessions(db: PixlDB, feature_id: str) -> bool:
    """Check if a feature has any running or paused sessions."""
    sessions = db.sessions.list_sessions(feature_id=feature_id)
    for session in sessions:
        ended_at = session.get("ended_at")
        if ended_at is None:
            return True
    return False


@register_hook("apply-triage-results")
def apply_triage_results_hook(ctx: HookContext) -> HookResult:
    """Apply triage decisions to the backlog deterministically."""
    db = PixlDB(ctx.project_root)
    db.initialize()

    payload = _get_triage_payload(ctx)
    decisions = payload.get("decisions", [])
    new_features_payload = payload.get("new_features", [])

    if not isinstance(decisions, list):
        return HookResult(success=False, error="Missing or invalid decisions in triage payload")

    applied: dict[str, list[str]] = {
        "mark_done": [],
        "defer": [],
        "remove": [],
        "reprioritize": [],
        "keep": [],
        "defer_fallback": [],
    }
    errors: list[str] = []

    for decision in decisions:
        if not isinstance(decision, dict):
            continue

        feature_id = str(decision.get("feature_id", "")).strip()
        action = str(decision.get("action", "")).strip()
        reason = str(decision.get("reason", ""))

        if not feature_id or not action:
            continue

        feature = db.backlog.get_feature(feature_id)
        if feature is None:
            errors.append(f"Feature not found: {feature_id}")
            continue

        if action == "keep":
            applied["keep"].append(feature_id)

        elif action == "mark_done":
            pr_url = decision.get("pr_url", "")
            note_parts = ["Marked done by replan triage"]
            if pr_url:
                note_parts.append(f"PR: {pr_url}")
            if reason:
                note_parts.append(f"Reason: {reason}")

            db.backlog.update_feature_status(
                feature_id,
                status="done",
                note=" | ".join(note_parts),
                trigger="replan_triage",
                trigger_id=ctx.session.id,
            )
            applied["mark_done"].append(feature_id)

        elif action == "defer":
            note = (
                f"Deferred by replan triage | Reason: {reason}"
                if reason
                else "Deferred by replan triage"
            )
            db.backlog.update_feature_status(
                feature_id,
                status="deferred",
                note=note,
                trigger="replan_triage",
                trigger_id=ctx.session.id,
            )
            applied["defer"].append(feature_id)

        elif action == "remove":
            # Safety: refuse to remove features with active sessions
            if _has_active_sessions(db, feature_id):
                note = (
                    f"Deferred instead of removed (active sessions exist) | Reason: {reason}"
                    if reason
                    else "Deferred instead of removed (active sessions exist)"
                )
                db.backlog.update_feature_status(
                    feature_id,
                    status="deferred",
                    note=note,
                    trigger="replan_triage",
                    trigger_id=ctx.session.id,
                )
                applied["defer_fallback"].append(feature_id)
            else:
                db.backlog.remove_feature(feature_id)
                applied["remove"].append(feature_id)

        elif action == "reprioritize":
            new_priority = str(decision.get("new_priority", "")).strip()
            if not new_priority:
                errors.append(f"Missing new_priority for reprioritize on {feature_id}")
                continue

            db.backlog.update_feature(feature_id, priority=new_priority)
            note = (
                f"Reprioritized to {new_priority} by replan triage | Reason: {reason}"
                if reason
                else f"Reprioritized to {new_priority} by replan triage"
            )
            db.backlog.update_feature_status(
                feature_id,
                status=str(feature.get("status", "backlog")),
                note=note,
                trigger="replan_triage",
                trigger_id=ctx.session.id,
            )
            applied["reprioritize"].append(feature_id)

    created_features: list[str] = []
    if isinstance(new_features_payload, list):
        for new_feat in new_features_payload:
            if not isinstance(new_feat, dict):
                continue

            title = str(new_feat.get("title", "")).strip()
            if not title:
                continue

            description = str(new_feat.get("description", ""))
            priority = str(new_feat.get("priority", "P2"))
            epic_id = new_feat.get("epic_id")
            depends_on = new_feat.get("depends_on", [])
            depends_on = depends_on if isinstance(depends_on, list) else []

            created = db.backlog.add_feature(
                title=title,
                description=description,
                priority=priority,
                epic_id=epic_id if isinstance(epic_id, str) else None,
                depends_on=depends_on if depends_on else None,
            )
            created_features.append(str(created["id"]))

    with contextlib.suppress(Exception):
        db.events.emit(
            event_type="triage_applied",
            session_id=ctx.session.id,
            entity_type="feature",
            entity_id=ctx.feature_id,
            payload={
                "applied": applied,
                "created_features": created_features,
                "errors": errors,
                "completed_at": datetime.now().isoformat(),
            },
        )

    return HookResult(
        success=True,
        data={
            "applied": applied,
            "created_features": created_features,
            "errors": errors,
        },
    )
