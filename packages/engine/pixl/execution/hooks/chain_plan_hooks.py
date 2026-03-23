"""Chain plan materialization hooks.

Implements deterministic, plan-only decomposition materialization:
- upsert features/dependencies from structured decomposition payload
- persist execution chain graph in plan_draft/plan_ready states
- write plan artifacts (JSON + Markdown)
- emit chain_plan_created event
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pixl.execution.hooks import HookContext, HookResult, register_hook
from pixl.storage.db.connection import PixlDB


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "node"


def _detect_cycle_nodes(dependency_map: dict[str, set[str]]) -> list[str]:
    color: dict[str, int] = dict.fromkeys(dependency_map, 0)
    path: list[str] = []
    cycle_nodes: set[str] = set()

    def dfs(node: str) -> None:
        color[node] = 1
        path.append(node)
        for dep in dependency_map.get(node, set()):
            if dep not in color:
                continue
            if color[dep] == 0:
                dfs(dep)
            elif color[dep] == 1:
                idx = path.index(dep)
                cycle_nodes.update(path[idx:])
        path.pop()
        color[node] = 2

    for node in sorted(dependency_map):
        if color[node] == 0:
            dfs(node)
    return sorted(cycle_nodes)


def _get_decompose_payload(ctx: HookContext) -> dict[str, Any]:
    source_node_id = str(ctx.params.get("source_node_id", "decompose"))
    structured = ctx.session.structured_outputs.get(source_node_id, {})
    if not isinstance(structured, dict):
        return {}
    payload = structured.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def _write_chain_plan_artifacts(
    artifacts_dir: Path,
    chain_payload: dict[str, Any],
    status: str,
) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    (artifacts_dir / "chain-plan.json").write_text(
        json.dumps(chain_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# Chain Plan")
    lines.append("")
    lines.append(f"- Status: `{status}`")
    lines.append(f"- Epic: `{chain_payload.get('epic_id', '')}`")
    lines.append(f"- Chain ID: `{chain_payload.get('chain_id', '')}`")
    lines.append("")
    lines.append("## Waves")
    for idx, wave in enumerate(chain_payload.get("waves", []), start=1):
        refs = ", ".join(wave)
        lines.append(f"{idx}. {refs}")
    lines.append("")
    lines.append("## Readiness")
    computed = chain_payload.get("validation", {}).get("computed", {})
    lines.append(f"- DAG valid: `{computed.get('dag_valid', False)}`")
    lines.append(f"- Cycles: `{computed.get('cycles_detected', [])}`")
    lines.append(f"- Orphans: `{computed.get('orphan_nodes', [])}`")
    lines.append(f"- Unknown refs: `{computed.get('unknown_refs', [])}`")
    lines.append("")

    (artifacts_dir / "chain-plan.md").write_text("\n".join(lines), encoding="utf-8")


@register_hook("materialize-chain-plan")
def materialize_chain_plan_hook(ctx: HookContext) -> HookResult:
    """Materialize a decomposition into backlog features + chain plan only.

    Never starts workflow sessions or queues execution.
    """
    db = PixlDB(ctx.project_root)
    db.initialize()

    payload = _get_decompose_payload(ctx)
    features_payload = payload.get("features", [])
    chain_plan = payload.get("chain_plan", {})
    validation_summary = payload.get("validation_summary", {})
    if not isinstance(features_payload, list) or not isinstance(chain_plan, dict):
        return HookResult(success=False, error="Missing or invalid decomposition payload")

    execution_feature = db.backlog.get_feature(ctx.feature_id)
    if execution_feature is None:
        return HookResult(success=False, error=f"Execution feature not found: {ctx.feature_id}")

    epic_id = execution_feature.get("epic_id")
    if not isinstance(epic_id, str) or not epic_id:
        return HookResult(
            success=False, error="materialize-chain-plan requires an epic-linked feature"
        )

    epic = db.backlog.get_epic(epic_id)
    if epic is None:
        return HookResult(success=False, error=f"Epic not found: {epic_id}")
    roadmap_id = epic.get("roadmap_id")

    # Deterministic feature upsert keyed by title within epic.
    existing_features = [
        feat
        for feat in db.backlog.list_features(epic_id=epic_id)
        if feat.get("type") != "execution"
    ]
    existing_by_title = {str(feat.get("title", "")): feat for feat in existing_features}

    feature_id_by_ref: dict[str, str] = {}
    workflow_by_ref: dict[str, str] = {}
    refinement_by_ref: dict[str, bool] = {}
    unknown_refs: set[str] = set()
    dependency_map: dict[str, set[str]] = {}

    for feature in features_payload:
        if not isinstance(feature, dict):
            continue
        title = str(feature.get("title", "")).strip()
        if not title:
            continue

        description = str(feature.get("description", ""))
        acceptance_criteria = feature.get("acceptance_criteria", [])
        if not isinstance(acceptance_criteria, list):
            acceptance_criteria = []
        acceptance_criteria = [str(item) for item in acceptance_criteria if str(item).strip()]
        owner = str(feature.get("owner", ""))
        risk_class = str(feature.get("risk_class", "low"))
        estimate_points = int(feature.get("estimate_points", 1))
        deps = feature.get("dependencies", [])
        deps = deps if isinstance(deps, list) else []
        dependency_map.setdefault(title, set())

        if title in existing_by_title:
            feature_id = str(existing_by_title[title]["id"])
            db.backlog.update_feature(
                feature_id,
                description=description,
                acceptance_criteria=acceptance_criteria,
                owner=owner,
                risk_class=risk_class,
                estimate_points=estimate_points,
            )
        else:
            created = db.backlog.add_feature(
                title=title,
                description=description,
                feature_type="feature",
                epic_id=epic_id,
                roadmap_id=roadmap_id,
                acceptance_criteria=acceptance_criteria,
            )
            feature_id = str(created["id"])
            db.backlog.update_feature(
                feature_id,
                acceptance_criteria=acceptance_criteria,
                owner=owner,
                risk_class=risk_class,
                estimate_points=estimate_points,
            )

        feature_id_by_ref[title] = feature_id
        sw = feature.get("suggested_workflow")
        if sw and isinstance(sw, str):
            workflow_by_ref[title] = sw
        if feature.get("needs_refinement"):
            refinement_by_ref[title] = True
        for dep in deps:
            dep_ref = str(dep)
            dependency_map[title].add(dep_ref)

    # Persist feature dependencies after IDs are known.
    for ref, feature_id in feature_id_by_ref.items():
        dep_ids: list[str] = []
        for dep_ref in sorted(dependency_map.get(ref, set())):
            dep_id = feature_id_by_ref.get(dep_ref)
            if dep_id:
                dep_ids.append(dep_id)
            else:
                unknown_refs.add(dep_ref)
        db.backlog.update_feature(feature_id, depends_on=dep_ids)

    # Build chain nodes (deterministic order from payload nodes, fallback to features order).
    payload_nodes = chain_plan.get("nodes", [])
    payload_nodes = payload_nodes if isinstance(payload_nodes, list) else []
    if not payload_nodes:
        payload_nodes = [
            {
                "feature_ref": ref,
                "wave": idx,
                "parallel_group": 0,
                "depends_on": [],
            }
            for idx, ref in enumerate(feature_id_by_ref.keys())
        ]

    chain_id = f"chain-{epic_id}"
    now = datetime.now().isoformat()

    node_rows: list[dict[str, Any]] = []
    node_id_by_ref: dict[str, str] = {}
    dependency_map_by_ref: dict[str, set[str]] = {ref: set() for ref in feature_id_by_ref}

    for idx, node in enumerate(payload_nodes, start=1):
        if not isinstance(node, dict):
            continue
        ref = str(node.get("feature_ref", "")).strip()
        if not ref:
            continue
        node_id = f"node-{idx:03d}-{_slug(ref)}"
        if ref not in feature_id_by_ref:
            unknown_refs.add(ref)
        node_id_by_ref.setdefault(ref, node_id)
        depends_on = node.get("depends_on", [])
        depends_on = depends_on if isinstance(depends_on, list) else []
        for dep in depends_on:
            dep_ref = str(dep)
            dependency_map_by_ref.setdefault(ref, set()).add(dep_ref)
            if dep_ref not in feature_id_by_ref:
                unknown_refs.add(dep_ref)
        node_rows.append(
            {
                "node_id": node_id,
                "feature_ref": ref,
                "feature_id": feature_id_by_ref.get(ref),
                "wave": int(node.get("wave", 0)),
                "parallel_group": int(node.get("parallel_group", 0)),
                "owner": (
                    execution_feature.get("owner")
                    if ref not in feature_id_by_ref
                    else db.backlog.get_feature(feature_id_by_ref[ref]).get("owner")
                ),
                "risk_class": (
                    execution_feature.get("risk_class")
                    if ref not in feature_id_by_ref
                    else db.backlog.get_feature(feature_id_by_ref[ref]).get("risk_class")
                ),
                "estimate_points": (
                    execution_feature.get("estimate_points")
                    if ref not in feature_id_by_ref
                    else db.backlog.get_feature(feature_id_by_ref[ref]).get("estimate_points")
                ),
                "suggested_workflow": node.get("suggested_workflow") or workflow_by_ref.get(ref),
                "needs_refinement": refinement_by_ref.get(ref, False),
            }
        )

    edge_pairs: set[tuple[str, str]] = set()
    payload_edges = chain_plan.get("edges", [])
    payload_edges = payload_edges if isinstance(payload_edges, list) else []
    for edge in payload_edges:
        if not isinstance(edge, dict):
            continue
        src_ref = str(edge.get("from", ""))
        dst_ref = str(edge.get("to", ""))
        src = node_id_by_ref.get(src_ref)
        dst = node_id_by_ref.get(dst_ref)
        if src and dst:
            edge_pairs.add((src, dst))
            dependency_map_by_ref.setdefault(dst_ref, set()).add(src_ref)
        else:
            if src_ref not in node_id_by_ref:
                unknown_refs.add(src_ref)
            if dst_ref not in node_id_by_ref:
                unknown_refs.add(dst_ref)

    for ref, deps in dependency_map_by_ref.items():
        dst = node_id_by_ref.get(ref)
        if not dst:
            continue
        for dep_ref in deps:
            src = node_id_by_ref.get(dep_ref)
            if src:
                edge_pairs.add((src, dst))

    # Semantic checks.
    cycle_nodes = _detect_cycle_nodes(
        {
            ref: {dep for dep in deps if dep in dependency_map_by_ref}
            for ref, deps in dependency_map_by_ref.items()
            if ref in dependency_map_by_ref
        }
    )
    incoming = dict.fromkeys(dependency_map_by_ref, 0)
    outgoing = dict.fromkeys(dependency_map_by_ref, 0)
    for src_ref, deps in dependency_map_by_ref.items():
        for dep in deps:
            if dep in incoming:
                incoming[src_ref] += 1
                outgoing[dep] += 1
    orphan_nodes = sorted(
        ref
        for ref in dependency_map_by_ref
        if incoming.get(ref, 0) == 0 and outgoing.get(ref, 0) == 0
    )
    dag_valid = not cycle_nodes and not unknown_refs
    status = "plan_ready" if dag_valid else "plan_draft"

    reported = validation_summary if isinstance(validation_summary, dict) else {}
    computed_summary = {
        "dag_valid": dag_valid,
        "cycles_detected": cycle_nodes,
        "orphan_nodes": orphan_nodes,
        "unknown_refs": sorted(unknown_refs),
    }

    execution_policy = chain_plan.get("execution_policy", {})
    if not isinstance(execution_policy, dict):
        execution_policy = {}
    max_parallel = int(execution_policy.get("max_parallel", 1))
    failure_policy = str(execution_policy.get("failure_policy", "branch_aware"))
    stop_on_failure = bool(execution_policy.get("stop_on_failure", False))
    source_session = db.sessions.get_session(ctx.session.id)
    source_session_id = ctx.session.id if source_session is not None else None

    db.conn.execute(
        """
        INSERT INTO execution_chains
            (id, epic_id, source_session_id, mode, status, max_parallel, failure_policy,
             stop_on_failure, validation_summary_json, created_at, updated_at)
        VALUES (?, ?, ?, 'plan_only', ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            max_parallel = excluded.max_parallel,
            failure_policy = excluded.failure_policy,
            stop_on_failure = excluded.stop_on_failure,
            validation_summary_json = excluded.validation_summary_json,
            updated_at = excluded.updated_at
        """,
        (
            chain_id,
            epic_id,
            source_session_id,
            status,
            max_parallel,
            failure_policy,
            1 if stop_on_failure else 0,
            json.dumps({"reported": reported, "computed": computed_summary}),
            now,
            now,
        ),
    )

    db.conn.execute("DELETE FROM execution_chain_nodes WHERE chain_id = ?", (chain_id,))
    db.conn.execute("DELETE FROM execution_chain_edges WHERE chain_id = ?", (chain_id,))

    for row in node_rows:
        initial_meta: dict[str, Any] = {}
        sw = row.get("suggested_workflow")
        if sw:
            initial_meta["suggested_workflow"] = sw
        if row.get("needs_refinement"):
            initial_meta["needs_refinement"] = True
        metadata_str = json.dumps(initial_meta, sort_keys=True) if initial_meta else "{}"
        db.conn.execute(
            """
            INSERT INTO execution_chain_nodes
                (chain_id, node_id, feature_id, feature_ref, wave, parallel_group, owner, risk_class,
                 estimate_points, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chain_id,
                row["node_id"],
                row["feature_id"],
                row["feature_ref"],
                row["wave"],
                row["parallel_group"],
                row["owner"],
                row["risk_class"],
                row["estimate_points"],
                metadata_str,
            ),
        )

    for src, dst in sorted(edge_pairs):
        db.conn.execute(
            """
            INSERT OR IGNORE INTO execution_chain_edges
                (chain_id, from_node_id, to_node_id)
            VALUES (?, ?, ?)
            """,
            (chain_id, src, dst),
        )

    db.conn.commit()

    chain_payload = {
        "chain_id": chain_id,
        "epic_id": epic_id,
        "status": status,
        "mode": "plan_only",
        "waves": chain_plan.get("waves", []),
        "execution_policy": {
            "max_parallel": max_parallel,
            "failure_policy": failure_policy,
            "stop_on_failure": stop_on_failure,
        },
        "validation": {
            "reported": reported,
            "computed": computed_summary,
        },
        "nodes": node_rows,
        "edges": [{"from": src, "to": dst} for src, dst in sorted(edge_pairs)],
    }
    _write_chain_plan_artifacts(ctx.artifacts_dir, chain_payload, status)

    db.events.emit(
        event_type="chain_plan_created",
        session_id=source_session_id,
        entity_type="epic",
        entity_id=epic_id,
        payload={"chain_id": chain_id, "status": status},
    )

    return HookResult(
        success=True,
        data={"chain_id": chain_id, "status": status, "epic_id": epic_id},
    )
