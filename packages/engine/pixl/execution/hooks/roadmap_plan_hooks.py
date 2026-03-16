"""Roadmap plan materialization hooks.

Implements deterministic, plan-only roadmap materialization:
- upsert milestones + milestone dependencies from structured roadmap plan payload
- upsert epics linked to roadmap + milestone with outcome/KPIs

This hook intentionally does not start execution sessions.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from pixl.execution.hooks import HookContext, HookResult, register_hook
from pixl.storage.db.connection import PixlDB


def _get_structured_payload(ctx: HookContext) -> dict[str, Any]:
    source_node_id = str(ctx.params.get("source_node_id", "plan-milestones"))
    structured = ctx.session.structured_outputs.get(source_node_id, {})
    if not isinstance(structured, dict):
        return {}
    payload = structured.get("payload", {})
    return payload if isinstance(payload, dict) else {}


@register_hook("materialize-roadmap-plan")
def materialize_roadmap_plan_hook(ctx: HookContext) -> HookResult:
    """Materialize a roadmap plan into milestones/epics deterministically."""
    db = PixlDB(ctx.project_root)
    db.initialize()

    execution_feature = db.backlog.get_feature(ctx.feature_id)
    if execution_feature is None:
        return HookResult(success=False, error=f"Execution feature not found: {ctx.feature_id}")

    roadmap_id = execution_feature.get("roadmap_id")
    if not isinstance(roadmap_id, str) or not roadmap_id:
        return HookResult(
            success=False, error="materialize-roadmap-plan requires a roadmap-linked feature"
        )

    if db.backlog.get_roadmap(roadmap_id) is None:
        return HookResult(success=False, error=f"Roadmap not found: {roadmap_id}")

    payload = _get_structured_payload(ctx)
    milestones_payload = payload.get("milestones", [])
    if not isinstance(milestones_payload, list) or not milestones_payload:
        return HookResult(
            success=False, error="Missing or invalid milestones in roadmap plan payload"
        )

    # Existing milestones keyed by name within roadmap.
    existing_ms_rows = db.conn.execute(
        "SELECT id, name FROM milestones WHERE roadmap_id = ?",
        (roadmap_id,),
    ).fetchall()
    milestone_id_by_name = {str(r["name"]): int(r["id"]) for r in existing_ms_rows}

    # Upsert milestones in deterministic order (payload order).
    for sort_order, ms in enumerate(milestones_payload):
        if not isinstance(ms, dict):
            continue
        name = str(ms.get("name", "")).strip()
        if not name:
            continue

        if name in milestone_id_by_name:
            db.conn.execute(
                "UPDATE milestones SET sort_order = ? WHERE id = ?",
                (int(sort_order), int(milestone_id_by_name[name])),
            )
        else:
            created = db.backlog.add_milestone(
                roadmap_id=roadmap_id,
                name=name,
                target_date=None,
                sort_order=int(sort_order),
            )
            milestone_id_by_name[name] = int(created["id"])

    milestone_ids = sorted(milestone_id_by_name.values())

    # Replace milestone dependencies deterministically for this roadmap.
    unknown_milestone_refs: set[str] = set()
    if milestone_ids:
        placeholders = ",".join("?" for _ in milestone_ids)
        db.conn.execute(
            f"DELETE FROM milestone_dependencies WHERE milestone_id IN ({placeholders})",
            milestone_ids,
        )

    for ms in milestones_payload:
        if not isinstance(ms, dict):
            continue
        name = str(ms.get("name", "")).strip()
        if not name or name not in milestone_id_by_name:
            continue
        ms_id = milestone_id_by_name[name]
        deps = ms.get("milestone_dependencies", [])
        deps = deps if isinstance(deps, list) else []
        for dep_name_raw in deps:
            dep_name = str(dep_name_raw).strip()
            if not dep_name:
                continue
            dep_id = milestone_id_by_name.get(dep_name)
            if dep_id is None:
                unknown_milestone_refs.add(dep_name)
                continue
            if dep_id == ms_id:
                continue
            db.conn.execute(
                """
                INSERT OR IGNORE INTO milestone_dependencies (milestone_id, depends_on_id)
                VALUES (?, ?)
                """,
                (ms_id, dep_id),
            )

    # Existing epics keyed by title within roadmap.
    existing_epic_rows = db.conn.execute(
        "SELECT id, title FROM epics WHERE roadmap_id = ?",
        (roadmap_id,),
    ).fetchall()
    epic_id_by_title = {str(r["title"]): str(r["id"]) for r in existing_epic_rows}

    created_epics = 0
    updated_epics = 0

    for ms in milestones_payload:
        if not isinstance(ms, dict):
            continue
        ms_name = str(ms.get("name", "")).strip()
        ms_id = milestone_id_by_name.get(ms_name)
        if not ms_id:
            continue

        epics_payload = ms.get("epics", [])
        epics_payload = epics_payload if isinstance(epics_payload, list) else []
        for epic_payload in epics_payload:
            if not isinstance(epic_payload, dict):
                continue
            title = str(epic_payload.get("title", "")).strip()
            if not title:
                continue
            scope = str(epic_payload.get("scope", ""))
            outcome = str(epic_payload.get("outcome", ""))
            kpis = epic_payload.get("kpis", [])
            kpis = kpis if isinstance(kpis, list) else []

            if title in epic_id_by_title:
                epic_id = epic_id_by_title[title]
                db.backlog.update_epic(
                    epic_id,
                    roadmap_id=roadmap_id,
                    milestone_id=ms_id,
                    original_prompt=scope,
                    outcome=outcome,
                    kpis=kpis,
                )
                updated_epics += 1
            else:
                created = db.backlog.add_epic(
                    title=title,
                    original_prompt=scope,
                    workflow_id=None,
                    outcome=outcome,
                    kpis=kpis,
                    roadmap_id=roadmap_id,
                    milestone_id=ms_id,
                    status="drafting",
                )
                epic_id_by_title[title] = str(created["id"])
                created_epics += 1

    db.conn.commit()

    with contextlib.suppress(Exception):
        db.events.emit(
            event_type="roadmap_plan_materialized",
            entity_type="roadmap",
            entity_id=roadmap_id,
            payload={
                "milestones": len(milestone_id_by_name),
                "epics_created": created_epics,
                "epics_updated": updated_epics,
                "unknown_milestone_refs": sorted(unknown_milestone_refs),
                "materialized_at": datetime.now().isoformat(),
            },
        )

    return HookResult(
        success=True,
        data={
            "roadmap_id": roadmap_id,
            "milestones": len(milestone_id_by_name),
            "epics_created": created_epics,
            "epics_updated": updated_epics,
            "unknown_milestone_refs": sorted(unknown_milestone_refs),
        },
    )
