"""Projection store — read-only SQL queries for dashboard views.

Provides pre-composed projections that join across multiple tables
to serve the Views API. All methods return plain dicts ready for
JSON serialisation.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from typing import Any

from pixl.storage.db.base import BaseStore

# Query limit constants
LIMIT_LIVE_RUNS = 50
LIMIT_RECOVERING = 50
LIMIT_RECENTLY_COMPLETED = 20
LIMIT_TOP_FAILURES = 5
LIMIT_BLOCKERS_PER_ROADMAP = 10
LIMIT_BLOCKERS_PER_EPIC = 20
LIMIT_GATE_RECENT_EVENTS = 5
LIMIT_ESCALATED_FEATURES = 20
LIMIT_RECOVERY_INBOX_EVENTS = 5

# Reusable SQL fragment for parent context (epic/roadmap) on execution features.
# Requires tables aliased as: f (features), e (epics), r (roadmaps).
_PARENT_CONTEXT_FRAGMENT = """
                CASE
                    WHEN f.type = 'execution' AND e.id IS NOT NULL THEN 'epic'
                    WHEN f.type = 'execution' AND r.id IS NOT NULL THEN 'roadmap'
                    ELSE NULL
                END AS parent_type,
                CASE
                    WHEN f.type = 'execution' THEN COALESCE(e.id, r.id)
                    ELSE NULL
                END AS parent_id,
                CASE
                    WHEN f.type = 'execution' THEN COALESCE(e.title, r.title)
                    ELSE NULL
                END AS parent_title,
                CASE
                    WHEN f.type = 'execution' THEN COALESCE(e.title, r.title, f.title, '')
                    ELSE COALESCE(f.title, '')
                END AS display_title"""


class ProjectionStore(BaseStore):
    """Read-only projection queries across the Pixl schema.

    Extends BaseStore for thread-safe PixlDB connection handling.
    """

    # factory_home

    def factory_home(self) -> dict[str, Any]:
        """Top-level operational dashboard data."""
        return {
            "live_runs": self._live_runs(),
            "pending_gates": self._pending_gates(),
            "recovering": self._recovering(),
            "recently_completed": self._recently_completed(),
            "health": self._health(),
            "autonomy": self._autonomy_overview(),
        }

    def _live_runs(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            f"""
            SELECT
                ws.id           AS session_id,
                ws.feature_id,
                COALESCE(f.title, '')  AS feature_title,
                f.type          AS feature_type,
                {_PARENT_CONTEXT_FRAGMENT},
                ni.node_id      AS current_node,
                ni.state         AS node_state,
                ws.started_at,
                ROUND(
                    (julianday('now') - julianday(ws.started_at)) * 24 * 60, 1
                ) AS elapsed_minutes
            FROM workflow_sessions ws
            JOIN node_instances ni
                ON ni.session_id = ws.id
                AND ni.state IN ('task_running', 'gate_waiting')
            LEFT JOIN features f ON f.id = ws.feature_id
            LEFT JOIN epics e ON e.id = f.epic_id
            LEFT JOIN roadmaps r ON r.id = f.roadmap_id
            WHERE ws.ended_at IS NULL
            ORDER BY ws.started_at DESC
            LIMIT {LIMIT_LIVE_RUNS}
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def _pending_gates(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            f"""
            SELECT
                ws.id           AS session_id,
                ni.node_id      AS gate_id,
                ws.feature_id,
                COALESCE(f.title, '')  AS feature_title,
                f.type          AS feature_type,
                {_PARENT_CONTEXT_FRAGMENT},
                ni.started_at   AS waiting_since
            FROM node_instances ni
            JOIN workflow_sessions ws ON ws.id = ni.session_id
            LEFT JOIN features f ON f.id = ws.feature_id
            LEFT JOIN epics e ON e.id = f.epic_id
            LEFT JOIN roadmaps r ON r.id = f.roadmap_id
            WHERE ni.state = 'gate_waiting'
            ORDER BY ni.started_at ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def _recovering(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            f"""
            SELECT
                ws.id           AS session_id,
                ni.node_id,
                ni.attempt,
                ws.feature_id,
                COALESCE(f.title, '') AS feature_title,
                f.type          AS feature_type,
                {_PARENT_CONTEXT_FRAGMENT},
                ni.started_at
            FROM node_instances ni
            JOIN workflow_sessions ws ON ws.id = ni.session_id
            LEFT JOIN features f ON f.id = ws.feature_id
            LEFT JOIN epics e ON e.id = f.epic_id
            LEFT JOIN roadmaps r ON r.id = f.roadmap_id
            WHERE ni.state = 'task_running'
              AND ni.attempt > 1
            ORDER BY ni.started_at DESC
            LIMIT {LIMIT_RECOVERING}
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def _recently_completed(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            f"""
            WITH latest_sessions AS (
                SELECT feature_id, id AS session_id,
                       ROW_NUMBER() OVER (PARTITION BY feature_id ORDER BY created_at DESC) AS rn
                FROM workflow_sessions
            )
            SELECT
                f.id,
                f.title,
                f.completed_at,
                EXISTS(
                    SELECT 1 FROM artifacts a WHERE a.feature_id = f.id
                ) AS has_artifacts,
                NOT EXISTS(
                    SELECT 1
                    FROM events e
                    WHERE e.session_id = ls.session_id
                      AND e.event_type = 'contract_violation'
                ) AS contracts_clean
            FROM features f
            LEFT JOIN latest_sessions ls ON ls.feature_id = f.id AND ls.rn = 1
            WHERE f.status = 'done'
              AND f.type != 'execution'
            ORDER BY f.completed_at DESC
            LIMIT {LIMIT_RECENTLY_COMPLETED}
            """
        ).fetchall()
        return [
            {
                **dict(r),
                "has_artifacts": bool(r["has_artifacts"]),
                "contracts_clean": bool(r["contracts_clean"]),
            }
            for r in rows
        ]

    def _health(self) -> dict[str, Any]:
        # Success rate: done / (done + failed) last 30 days
        row = self._conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END), 0) AS done,
                COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) AS failed
            FROM features
            WHERE (
                completed_at >= datetime('now', '-30 days')
                OR (status = 'failed' AND updated_at >= datetime('now', '-30 days'))
            )
              AND type != 'execution'
            """
        ).fetchone()
        done = row["done"] if row else 0
        failed = row["failed"] if row else 0
        total = done + failed
        success_rate = round(done * 1.0 / total, 3) if total > 0 else 0.0

        # Mean recovery time (minutes between recovery_requested and recovery_succeeded)
        mrt_row = self._conn.execute(
            """
            SELECT AVG(
                (julianday(e2.created_at) - julianday(e1.created_at)) * 24 * 60
            ) AS mean_minutes
            FROM events e1
            JOIN events e2
                ON e2.session_id = e1.session_id
                AND e2.event_type = 'recovery_succeeded'
                AND e2.created_at > e1.created_at
            WHERE e1.event_type = 'recovery_requested'
              AND e1.created_at >= datetime('now', '-30 days')
            """
        ).fetchone()
        mean_recovery_minutes = (
            round(mrt_row["mean_minutes"], 2) if mrt_row and mrt_row["mean_minutes"] else 0.0
        )

        # Top failure signatures
        sig_rows = self._conn.execute(
            f"""
            SELECT
                error_type,
                COUNT(*) AS count
            FROM incidents
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT {LIMIT_TOP_FAILURES}
            """
        ).fetchall()
        top_failure_signatures = [dict(r) for r in sig_rows]

        return {
            "success_rate": success_rate,
            "mean_recovery_minutes": mean_recovery_minutes,
            "top_failure_signatures": top_failure_signatures,
        }

    def _autonomy_overview(self) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total_outcomes,
                ROUND(COALESCE(AVG(confidence), 0.0), 3) AS avg_confidence,
                COALESCE(SUM(auto_approved_gates), 0) AS auto_approved_gates,
                COALESCE(SUM(manual_gate_approvals), 0) AS manual_gate_approvals,
                COALESCE(SUM(gate_rejections), 0) AS gate_rejections,
                COALESCE(SUM(recovery_cycles), 0) AS recovery_cycles,
                COALESCE(SUM(human_interventions), 0) AS human_interventions,
                COALESCE(SUM(CASE WHEN mode = 'autopilot' THEN 1 ELSE 0 END), 0) AS autopilot_runs
            FROM autonomy_outcomes
            WHERE created_at >= datetime('now', '-30 days')
            """
        ).fetchone()

        if not row:
            return {
                "total_outcomes": 0,
                "avg_confidence": 0.0,
                "auto_approved_gates": 0,
                "manual_gate_approvals": 0,
                "gate_rejections": 0,
                "recovery_cycles": 0,
                "human_interventions": 0,
                "autopilot_runs": 0,
            }

        return dict(row)

    # roadmap_rollup

    def roadmap_rollup(self, roadmap_id: str | None = None) -> list[dict[str, Any]]:
        """Rollup view of roadmaps with epic/feature counts and progress."""
        where = "WHERE r.id = ?" if roadmap_id else ""
        params: tuple[Any, ...] = (roadmap_id,) if roadmap_id else ()

        rows = self._conn.execute(
            f"""
            SELECT
                r.id,
                r.title,
                r.status,
                r.created_at,
                r.completed_at,
                COALESCE(agg.epic_count, 0)            AS epic_count,
                COALESCE(agg.feature_count, 0)         AS feature_count,
                COALESCE(agg.features_done, 0)         AS features_done,
                COALESCE(agg.features_total, 0)        AS features_total,
                COALESCE(agg.features_in_progress, 0)  AS features_in_progress,
                CASE
                    WHEN COALESCE(agg.features_total, 0) > 0
                    THEN ROUND(COALESCE(agg.features_done, 0) * 100.0
                               / agg.features_total, 1)
                    ELSE 0.0
                END AS progress_pct
            FROM roadmaps r
            LEFT JOIN (
                SELECT
                    r2.id AS roadmap_id,
                    COUNT(DISTINCT e.id) AS epic_count,
                    COUNT(DISTINCT f.id) AS feature_count,
                    COALESCE(SUM(CASE WHEN f.status = 'done' THEN 1 ELSE 0 END), 0)
                        AS features_done,
                    COUNT(f.id) AS features_total,
                    COALESCE(SUM(CASE WHEN f.status = 'in_progress' THEN 1 ELSE 0 END), 0)
                        AS features_in_progress
                FROM roadmaps r2
                LEFT JOIN epics e ON e.roadmap_id = r2.id
                LEFT JOIN features f
                    ON (f.epic_id = e.id OR f.roadmap_id = r2.id)
                    AND f.type != 'execution'
                GROUP BY r2.id
            ) agg ON agg.roadmap_id = r.id
            {where}
            ORDER BY r.created_at DESC
            """,
            params,
        ).fetchall()

        if not rows:
            return []

        roadmap_ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(roadmap_ids))

        # Bulk: top blockers per roadmap
        blocker_rows = self._conn.execute(
            f"""
            SELECT f.id, f.title, f.blocked_reason,
                   COALESCE(f.roadmap_id, e.roadmap_id) AS roadmap_id
            FROM features f
            LEFT JOIN epics e ON e.id = f.epic_id
            WHERE f.status = 'blocked'
              AND f.type != 'execution'
              AND COALESCE(f.roadmap_id, e.roadmap_id) IN ({placeholders})
            """,
            tuple(roadmap_ids),
        ).fetchall()
        blockers_by_roadmap: dict[str, list[dict[str, Any]]] = {rid: [] for rid in roadmap_ids}
        for b in blocker_rows:
            bd = dict(b)
            rid = bd.pop("roadmap_id")
            if (
                rid in blockers_by_roadmap
                and len(blockers_by_roadmap[rid]) < LIMIT_BLOCKERS_PER_ROADMAP
            ):
                blockers_by_roadmap[rid].append(bd)

        # Bulk: confidence per roadmap (incident failure rate)
        conf_rows = self._conn.execute(
            f"""
            SELECT
                COALESCE(f.roadmap_id, e.roadmap_id) AS roadmap_id,
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN i.outcome = 'failed' THEN 1 ELSE 0 END), 0) AS failed
            FROM incidents i
            JOIN features f ON f.id = i.feature_id
            LEFT JOIN epics e ON e.id = f.epic_id
            WHERE COALESCE(f.roadmap_id, e.roadmap_id) IN ({placeholders})
              AND f.type != 'execution'
            GROUP BY COALESCE(f.roadmap_id, e.roadmap_id)
            """,
            tuple(roadmap_ids),
        ).fetchall()
        conf_by_roadmap: dict[str, dict[str, int]] = {}
        for cr in conf_rows:
            conf_by_roadmap[cr["roadmap_id"]] = {"total": cr["total"], "failed": cr["failed"]}

        results = []
        for r in rows:
            d = dict(r)
            rid = d["id"]
            d["top_blockers"] = blockers_by_roadmap.get(rid, [])

            conf = conf_by_roadmap.get(rid)
            if conf and conf["total"] > 0:
                d["confidence"] = round(1.0 - (conf["failed"] / conf["total"]), 3)
            else:
                d["confidence"] = 1.0

            results.append(d)

        return results

    # epic_rollup

    def epic_rollup(self, epic_id: str | None = None) -> list[dict[str, Any]]:
        """Rollup view of epics with feature status breakdown."""
        where = "WHERE e.id = ?" if epic_id else ""
        params: tuple[Any, ...] = (epic_id,) if epic_id else ()

        rows = self._conn.execute(
            f"""
            SELECT
                e.id,
                e.title,
                e.status,
                e.roadmap_id,
                e.created_at,
                e.completed_at,
                COALESCE(SUM(CASE WHEN f.status = 'backlog'     THEN 1 ELSE 0 END), 0) AS backlog,
                COALESCE(SUM(CASE WHEN f.status = 'planned'     THEN 1 ELSE 0 END), 0) AS planned,
                COALESCE(SUM(CASE WHEN f.status = 'in_progress' THEN 1 ELSE 0 END), 0) AS in_progress,
                COALESCE(SUM(CASE WHEN f.status = 'review'      THEN 1 ELSE 0 END), 0) AS review,
                COALESCE(SUM(CASE WHEN f.status = 'blocked'     THEN 1 ELSE 0 END), 0) AS blocked,
                COALESCE(SUM(CASE WHEN f.status = 'done'        THEN 1 ELSE 0 END), 0) AS done,
                COALESCE(SUM(CASE WHEN f.status = 'failed'      THEN 1 ELSE 0 END), 0) AS failed,
                COUNT(f.id) AS feature_count
            FROM epics e
            LEFT JOIN features f ON f.epic_id = e.id AND f.type != 'execution'
            {where}
            GROUP BY e.id
            ORDER BY e.created_at DESC
            """,
            params,
        ).fetchall()

        if not rows:
            return []

        epic_ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(epic_ids))

        # Bulk: active runs per epic
        active_rows = self._conn.execute(
            f"""
            SELECT f.epic_id, COUNT(*) AS cnt
            FROM workflow_sessions ws
            JOIN features f ON f.id = ws.feature_id
            WHERE f.epic_id IN ({placeholders})
              AND ws.ended_at IS NULL
            GROUP BY f.epic_id
            """,
            tuple(epic_ids),
        ).fetchall()
        active_by_epic: dict[str, int] = {ar["epic_id"]: ar["cnt"] for ar in active_rows}

        # Bulk: blockers per epic (blocked features + gate-waiting)
        blocker_rows = self._conn.execute(
            f"""
            SELECT f.id, f.title, 'blocked' AS reason_type, f.blocked_reason, f.epic_id
            FROM features f
            WHERE f.epic_id IN ({placeholders})
              AND f.status = 'blocked'
              AND f.type != 'execution'
            UNION ALL
            SELECT f.id, f.title, 'gate_waiting' AS reason_type, ni.node_id AS blocked_reason, f.epic_id
            FROM node_instances ni
            JOIN workflow_sessions ws ON ws.id = ni.session_id
            JOIN features f ON f.id = ws.feature_id
            WHERE f.epic_id IN ({placeholders})
              AND ni.state = 'gate_waiting'
              AND f.type != 'execution'
            """,
            tuple(epic_ids) + tuple(epic_ids),
        ).fetchall()
        blockers_by_epic: dict[str, list[dict[str, Any]]] = {eid: [] for eid in epic_ids}
        for b in blocker_rows:
            bd = dict(b)
            eid = bd.pop("epic_id")
            if eid in blockers_by_epic and len(blockers_by_epic[eid]) < LIMIT_BLOCKERS_PER_EPIC:
                blockers_by_epic[eid].append(bd)

        results = []
        for r in rows:
            d = dict(r)
            eid = d["id"]

            d["features_by_status"] = {
                "backlog": d.pop("backlog"),
                "planned": d.pop("planned"),
                "in_progress": d.pop("in_progress"),
                "review": d.pop("review"),
                "blocked": d.pop("blocked"),
                "done": d.pop("done"),
                "failed": d.pop("failed"),
            }

            d["active_runs"] = active_by_epic.get(eid, 0)
            d["blockers"] = blockers_by_epic.get(eid, [])

            results.append(d)

        return results

    def epic_execution_plan(self, epic_id: str) -> dict[str, Any] | None:
        """Plan-only chain graph/readiness for an epic."""
        chain_row = self._conn.execute(
            """
            SELECT
                id,
                epic_id,
                mode,
                status,
                max_parallel,
                failure_policy,
                stop_on_failure,
                validation_summary_json,
                created_at,
                updated_at
            FROM execution_chains
            WHERE epic_id = ?
            """,
            (epic_id,),
        ).fetchone()
        if chain_row is None:
            return None

        chain = dict(chain_row)
        chain_id = str(chain["id"])

        node_rows = self._conn.execute(
            """
            SELECT
                node_id,
                feature_id,
                feature_ref,
                wave,
                parallel_group,
                owner,
                risk_class,
                estimate_points,
                status,
                session_id,
                attempt_count,
                started_at,
                completed_at,
                error
            FROM execution_chain_nodes
            WHERE chain_id = ?
            ORDER BY wave ASC, parallel_group ASC, node_id ASC
            """,
            (chain_id,),
        ).fetchall()
        nodes = [dict(r) for r in node_rows]
        node_ids = {str(n["node_id"]) for n in nodes}
        node_by_id = {str(n["node_id"]): n for n in nodes}

        edge_rows = self._conn.execute(
            """
            SELECT from_node_id, to_node_id
            FROM execution_chain_edges
            WHERE chain_id = ?
            ORDER BY from_node_id ASC, to_node_id ASC
            """,
            (chain_id,),
        ).fetchall()
        edges = [{"from": str(r["from_node_id"]), "to": str(r["to_node_id"])} for r in edge_rows]

        wave_violations: list[dict[str, str]] = []
        dangling_edges: list[str] = []
        incoming: dict[str, int] = dict.fromkeys(node_ids, 0)
        outgoing: dict[str, int] = dict.fromkeys(node_ids, 0)
        for edge in edges:
            src = edge["from"]
            dst = edge["to"]
            src_node = node_by_id.get(src)
            dst_node = node_by_id.get(dst)
            if src_node is None or dst_node is None:
                dangling_edges.append(f"{src}->{dst}")
                continue
            incoming[dst] += 1
            outgoing[src] += 1
            if int(src_node.get("wave", 0)) >= int(dst_node.get("wave", 0)):
                wave_violations.append(
                    {
                        "from": src_node.get("feature_ref", src),
                        "to": dst_node.get("feature_ref", dst),
                        "reason": "dependency_wave_order",
                    }
                )

        wave_groups: dict[int, list[dict[str, Any]]] = {}
        for node in nodes:
            wave = int(node.get("wave", 0))
            wave_groups.setdefault(wave, []).append(node)
        waves = [
            {
                "wave": wave,
                "nodes": [
                    {
                        "node_id": str(node.get("node_id")),
                        "feature_ref": str(node.get("feature_ref", "")),
                        "parallel_group": int(node.get("parallel_group", 0)),
                        "owner": node.get("owner"),
                        "risk_class": node.get("risk_class"),
                        "estimate_points": node.get("estimate_points"),
                        "status": node.get("status"),
                        "session_id": node.get("session_id"),
                        "attempt_count": node.get("attempt_count"),
                        "started_at": node.get("started_at"),
                        "completed_at": node.get("completed_at"),
                        "error": node.get("error"),
                    }
                    for node in wave_groups[wave]
                ],
            }
            for wave in sorted(wave_groups)
        ]

        orphan_nodes = [
            str(node_by_id[node_id].get("feature_ref", node_id))
            for node_id in sorted(node_ids)
            if incoming.get(node_id, 0) == 0 and outgoing.get(node_id, 0) == 0
        ]

        validation = self._normalise_validation_summary(chain.get("validation_summary_json"))
        dag_valid = bool(validation.get("dag_valid", False))
        cycles_detected = [str(v) for v in validation.get("cycles_detected", [])]

        blockers: list[str] = []
        if not dag_valid:
            blockers.append("dag_invalid")
        if cycles_detected:
            blockers.append("cycles_detected")
        if dangling_edges:
            blockers.append("dangling_edges")
        if wave_violations:
            blockers.append("dependency_wave_violations")

        checks = [
            {
                "id": "dag_valid",
                "ok": dag_valid,
                "detail": "Validation summary reports a DAG without unknown refs.",
            },
            {
                "id": "cycles_detected",
                "ok": len(cycles_detected) == 0,
                "detail": "No cyclic dependencies in chain edges.",
            },
            {
                "id": "dangling_edges",
                "ok": len(dangling_edges) == 0,
                "detail": "All edges connect to known plan nodes.",
            },
            {
                "id": "dependency_wave_violations",
                "ok": len(wave_violations) == 0,
                "detail": "All dependency edges point to a later wave.",
            },
        ]

        return {
            "chain_id": chain_id,
            "epic_id": epic_id,
            "mode": str(chain.get("mode", "plan_only")),
            "status": str(chain.get("status", "plan_draft")),
            "execution_policy": {
                "max_parallel": int(chain.get("max_parallel", 1)),
                "failure_policy": str(chain.get("failure_policy", "branch_aware")),
                "stop_on_failure": bool(chain.get("stop_on_failure", 0)),
            },
            "nodes": nodes,
            "edges": edges,
            "waves": waves,
            "validation_summary": {
                "dag_valid": dag_valid,
                "cycles_detected": cycles_detected,
                "orphan_nodes": orphan_nodes,
                "notes": [str(v) for v in validation.get("notes", [])],
            },
            "readiness": {
                "ready": (
                    str(chain.get("status", "")) == "plan_ready"
                    and dag_valid
                    and len(dangling_edges) == 0
                    and len(wave_violations) == 0
                ),
                "checks": checks,
                "blockers": blockers,
                "dependency_issues": wave_violations,
                "dangling_edges": sorted(dangling_edges),
            },
            "updated_at": chain.get("updated_at"),
            "created_at": chain.get("created_at"),
        }

    # chain_health

    def chain_health(self) -> dict[str, Any]:
        """High-level chain runner health metrics for dashboards."""
        row = self._conn.execute(
            """
            SELECT
                SUM(CASE WHEN status IN ('running', 'paused') THEN 1 ELSE 0 END) AS active_chains,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running_chains,
                SUM(CASE WHEN status = 'paused' THEN 1 ELSE 0 END) AS paused_chains,
                SUM(CASE WHEN status = 'plan_ready' THEN 1 ELSE 0 END) AS plan_ready_chains,
                SUM(CASE WHEN status = 'plan_draft' THEN 1 ELSE 0 END) AS plan_draft_chains,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_chains,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_chains,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_chains,
                COUNT(*) AS total_chains
            FROM execution_chains
            """
        ).fetchone()

        summary = dict(row) if row else {}

        blocked_nodes = self._conn.execute(
            """
            SELECT COUNT(*) AS blocked_nodes
            FROM execution_chain_nodes n
            JOIN execution_chains c ON c.id = n.chain_id
            WHERE c.status IN ('running', 'paused')
              AND n.status = 'blocked'
            """
        ).fetchone()

        terminal_last_30d = self._conn.execute(
            """
            SELECT
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status IN ('completed', 'failed', 'cancelled') THEN 1 ELSE 0 END) AS terminal
            FROM execution_chains
            WHERE COALESCE(updated_at, created_at) >= datetime('now', '-30 days')
              AND status IN ('completed', 'failed', 'cancelled')
            """
        ).fetchone()

        terminal_dict = dict(terminal_last_30d) if terminal_last_30d else {}
        completed = int(terminal_dict.get("completed") or 0)
        terminal = int(terminal_dict.get("terminal") or 0)
        completion_rate_30d = round(completed / terminal, 3) if terminal else 0.0

        blocked_dict = dict(blocked_nodes) if blocked_nodes else {}
        return {
            "chains": summary,
            "blocked_nodes": int(blocked_dict.get("blocked_nodes") or 0),
            "completion_rate_30d": completion_rate_30d,
        }

    # contract_completeness

    def contract_completeness(self) -> dict[str, Any]:
        """Contract metadata completeness ratios for PRD decomposition quality."""
        feat_row = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN owner IS NOT NULL AND TRIM(owner) != ''
                         AND risk_class IS NOT NULL AND TRIM(risk_class) != ''
                         AND estimate_points IS NOT NULL AND estimate_points > 0
                         AND acceptance_criteria_json IS NOT NULL
                         AND acceptance_criteria_json != '[]'
                        THEN 1 ELSE 0
                    END
                ) AS complete
            FROM features
            WHERE type != 'execution'
            """
        ).fetchone()
        epic_row = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN outcome IS NOT NULL AND TRIM(outcome) != ''
                         AND kpis_json IS NOT NULL AND kpis_json != '[]'
                        THEN 1 ELSE 0
                    END
                ) AS complete
            FROM epics
            """
        ).fetchone()

        feat_dict = dict(feat_row) if feat_row else {}
        epic_dict = dict(epic_row) if epic_row else {}

        features_total = int(feat_dict.get("total") or 0)
        features_complete = int(feat_dict.get("complete") or 0)
        epics_total = int(epic_dict.get("total") or 0)
        epics_complete = int(epic_dict.get("complete") or 0)

        overall_total = features_total + epics_total
        overall_complete = features_complete + epics_complete

        return {
            "features": {
                "complete": features_complete,
                "total": features_total,
                "ratio": round(features_complete / features_total, 3) if features_total else 0.0,
            },
            "epics": {
                "complete": epics_complete,
                "total": epics_total,
                "ratio": round(epics_complete / epics_total, 3) if epics_total else 0.0,
            },
            "overall": {
                "complete": overall_complete,
                "total": overall_total,
                "ratio": round(overall_complete / overall_total, 3) if overall_total else 0.0,
            },
        }

    # feature_detail

    def feature_detail(self, feature_id: str) -> dict[str, Any] | None:
        """Rich detail view for a single feature."""
        row = self._conn.execute("SELECT * FROM features WHERE id = ?", (feature_id,)).fetchone()
        if row is None:
            return None

        d = dict(row)

        for jf in ("success_criteria_json", "assumptions_json"):
            if jf in d and isinstance(d[jf], str):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d[jf] = json.loads(d[jf])

        # Current session
        sess_row = self._conn.execute(
            """
            SELECT * FROM workflow_sessions
            WHERE feature_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (feature_id,),
        ).fetchone()
        d["current_session"] = dict(sess_row) if sess_row else None

        session_id = sess_row["id"] if sess_row else None

        # Pipeline: node instances for current session
        if session_id:
            ni_rows = self._conn.execute(
                """
                SELECT * FROM node_instances
                WHERE session_id = ?
                ORDER BY ready_at ASC
                """,
                (session_id,),
            ).fetchall()
            d["pipeline"] = [self._node_to_dict(nr) for nr in ni_rows]
        else:
            d["pipeline"] = []

        # Timeline: last 50 events
        timeline_rows = self._conn.execute(
            """
            SELECT * FROM events
            WHERE entity_id = ?
               OR session_id IN (
                   SELECT id FROM workflow_sessions WHERE feature_id = ?
               )
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (feature_id, feature_id),
        ).fetchall()
        d["timeline"] = [self._event_to_dict(er) for er in timeline_rows]

        # Artifacts
        art_rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE feature_id = ?",
            (feature_id,),
        ).fetchall()
        d["artifacts"] = [self._artifact_to_dict(ar) for ar in art_rows]

        # Recovery attempts
        inc_rows = self._conn.execute(
            "SELECT * FROM incidents WHERE feature_id = ?",
            (feature_id,),
        ).fetchall()
        d["recovery_attempts"] = [self._incident_to_dict(ir) for ir in inc_rows]

        # Evidence
        has_contract_violation = False
        if session_id:
            cv_row = self._conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM events
                WHERE session_id = ? AND event_type = 'contract_violation'
                """,
                (session_id,),
            ).fetchone()
            has_contract_violation = (cv_row["cnt"] > 0) if cv_row else False

        has_test_artifact = any(a.get("type") == "test" for a in d["artifacts"])

        d["evidence"] = {
            "contracts_passed": not has_contract_violation,
            "tests_passed": has_test_artifact,
            "has_pr": d.get("pr_url") is not None,
            "has_plan": d.get("plan_path") is not None,
        }

        return d

    # gate_inbox

    def gate_inbox(self) -> list[dict[str, Any]]:
        """All gates waiting for human approval, with evidence bundles."""
        rows = self._conn.execute(
            """
            SELECT
                ni.session_id,
                ni.node_id      AS gate_id,
                ni.started_at   AS waiting_since,
                ws.feature_id,
                COALESCE(f.title, '') AS feature_title,
                COALESCE(c.value, 'assist') AS autonomy_mode
            FROM node_instances ni
            JOIN workflow_sessions ws ON ws.id = ni.session_id
            LEFT JOIN features f ON f.id = ws.feature_id
            LEFT JOIN config c ON c.key = ('autonomy:' || ws.feature_id)
            WHERE ni.state = 'gate_waiting'
            ORDER BY ni.started_at ASC
            """
        ).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            sid = d["session_id"]

            # Recent events before gate
            recent_events = self._conn.execute(
                f"""
                SELECT * FROM events
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT {LIMIT_GATE_RECENT_EVENTS}
                """,
                (sid,),
            ).fetchall()

            # Artifacts for the session
            artifacts = self._conn.execute(
                "SELECT * FROM artifacts WHERE session_id = ?",
                (sid,),
            ).fetchall()

            # Contract results
            contract_events = self._conn.execute(
                """
                SELECT * FROM events
                WHERE session_id = ?
                  AND event_type IN ('contract_passed', 'contract_violation')
                ORDER BY created_at DESC
                """,
                (sid,),
            ).fetchall()

            feature_id = d.get("feature_id")
            autonomy_profile = None
            if feature_id:
                profile_row = self._conn.execute(
                    """
                    SELECT agent_name, task_key, level, confidence, samples, updated_at
                    FROM autonomy_profiles
                    WHERE feature_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (feature_id,),
                ).fetchone()
                if profile_row:
                    autonomy_profile = dict(profile_row)

            d["autonomy_profile"] = autonomy_profile
            d["evidence_bundle"] = {
                "recent_events": [self._event_to_dict(e) for e in recent_events],
                "artifacts": [self._artifact_to_dict(a) for a in artifacts],
                "contract_results": [self._event_to_dict(e) for e in contract_events],
            }
            results.append(d)

        return results

    # recovery_inbox

    def recovery_inbox(self) -> list[dict[str, Any]]:
        """All blocked nodes awaiting human intervention, with diagnostics."""
        rows = self._conn.execute(
            """
            SELECT
                ni.session_id,
                ni.node_id,
                ni.blocked_reason,
                ni.error_message,
                ni.failure_kind,
                ni.started_at   AS blocked_since,
                ws.feature_id,
                COALESCE(f.title, '') AS feature_title
            FROM node_instances ni
            JOIN workflow_sessions ws ON ws.id = ni.session_id
            LEFT JOIN features f ON f.id = ws.feature_id
            WHERE ni.state = 'task_blocked'
            ORDER BY ni.started_at ASC
            """
        ).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            sid = d["session_id"]

            # Blocker artifact: most recent task_blocked event payload
            blocker_event = self._conn.execute(
                """
                SELECT payload_json FROM events
                WHERE session_id = ? AND event_type = 'task_blocked'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (sid,),
            ).fetchone()
            blocker_artifact = None
            if blocker_event and blocker_event["payload_json"]:
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    payload = json.loads(blocker_event["payload_json"])
                    blocker_artifact = payload.get("reason") or payload.get("message")

            # Recent recovery events for this session
            recovery_events = self._conn.execute(
                f"""
                SELECT * FROM events
                WHERE session_id = ?
                  AND (event_type LIKE 'recovery_%' OR event_type = 'session_reclaimed')
                ORDER BY created_at DESC
                LIMIT {LIMIT_RECOVERY_INBOX_EVENTS}
                """,
                (sid,),
            ).fetchall()

            d["blocker_artifact"] = blocker_artifact
            d["recovery_events"] = [self._event_to_dict(e) for e in recovery_events]
            results.append(d)

        return results

    # recovery_lab

    def recovery_lab(self) -> dict[str, Any]:
        """Recovery analytics dashboard."""
        # Failure signatures
        sig_rows = self._conn.execute(
            """
            SELECT
                error_type,
                COUNT(*) AS count,
                MAX(created_at) AS last_seen
            FROM incidents
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY error_type
            ORDER BY count DESC
            """
        ).fetchall()

        # Recovery success rate by action
        action_rows = self._conn.execute(
            """
            SELECT
                recovery_action,
                COUNT(*) AS attempted,
                COALESCE(SUM(CASE WHEN outcome = 'succeeded' THEN 1 ELSE 0 END), 0)
                    AS succeeded,
                CASE
                    WHEN COUNT(*) > 0
                    THEN ROUND(
                        SUM(CASE WHEN outcome = 'succeeded' THEN 1 ELSE 0 END) * 1.0
                        / COUNT(*), 3
                    )
                    ELSE 0.0
                END AS rate
            FROM incidents
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY recovery_action
            ORDER BY attempted DESC
            """
        ).fetchall()

        # Trend: incidents per day last 30 days
        trend_rows = self._conn.execute(
            """
            SELECT
                DATE(created_at) AS day,
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN outcome = 'succeeded' THEN 1 ELSE 0 END), 0)
                    AS succeeded,
                COALESCE(SUM(CASE WHEN outcome = 'failed' THEN 1 ELSE 0 END), 0)
                    AS failed,
                COALESCE(SUM(CASE WHEN outcome = 'escalated' THEN 1 ELSE 0 END), 0)
                    AS escalated
            FROM incidents
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """
        ).fetchall()

        # Human gate triggers: recovery_escalated grouped by feature
        escalated_rows = self._conn.execute(
            f"""
            SELECT
                COALESCE(e.entity_id, ws.feature_id) AS feature_id,
                COALESCE(f.title, '') AS feature_title,
                COUNT(*) AS escalation_count
            FROM events e
            LEFT JOIN workflow_sessions ws ON ws.id = e.session_id
            LEFT JOIN features f ON f.id = COALESCE(e.entity_id, ws.feature_id)
            WHERE e.event_type = 'recovery_escalated'
              AND e.created_at >= datetime('now', '-30 days')
            GROUP BY feature_id
            ORDER BY escalation_count DESC
            LIMIT {LIMIT_ESCALATED_FEATURES}
            """
        ).fetchall()

        return {
            "failure_signatures": [dict(r) for r in sig_rows],
            "recovery_success_rate": [dict(r) for r in action_rows],
            "trend": [dict(r) for r in trend_rows],
            "human_gate_triggers": [dict(r) for r in escalated_rows],
        }

    # Row helpers

    @staticmethod
    def _row_with_json(row: sqlite3.Row, *json_fields: str) -> dict[str, Any]:
        """Convert a row to dict, parsing specified JSON string fields in-place."""
        d = dict(row)
        for jf in json_fields:
            if jf in d and isinstance(d[jf], str):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d[jf] = json.loads(d[jf])
        return d

    @staticmethod
    def _node_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return ProjectionStore._row_with_json(row, "output_json")

    @staticmethod
    def _event_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return ProjectionStore._row_with_json(row, "payload_json")

    @staticmethod
    def _artifact_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return ProjectionStore._row_with_json(row, "tags_json", "extra_json", "references_json")

    _incident_to_dict = _event_to_dict

    @staticmethod
    def _normalise_validation_summary(raw: Any) -> dict[str, Any]:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = {}
        if not isinstance(raw, dict):
            raw = {}
        if isinstance(raw.get("computed"), dict):
            raw = raw["computed"]
        return {
            "dag_valid": bool(raw.get("dag_valid", False)),
            "cycles_detected": list(raw.get("cycles_detected", [])),
            "orphan_nodes": list(raw.get("orphan_nodes", [])),
            "notes": list(raw.get("notes", [])),
        }
