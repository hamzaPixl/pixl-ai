"""Backlog store: roadmaps, epics, features with relational integrity.

Replaces the JSON-based BacklogStore with proper relational storage.
All entities use foreign keys for the hierarchy:
    Roadmap -> Epic -> Feature

Feature dependencies are stored in a junction table with
cycle detection and topological ordering support.

THREAD SAFETY: Receives PixlDB and gets thread-local connections
for each operation, making it safe for concurrent use.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from pixl.storage.db.base import BaseStore

_ROADMAP_FIELDS = frozenset(
    {
        "title",
        "description",
        "status",
        "vision",
        "time_horizon",
        "updated_at",
        "completed_at",
        "original_prompt",
    }
)
_EPIC_FIELDS = frozenset(
    {
        "title",
        "description",
        "status",
        "priority",
        "kpis_json",
        "updated_at",
        "completed_at",
        "workflow_id",
        "original_prompt",
        "roadmap_id",
    }
)
_FEATURE_FIELDS = frozenset(
    {
        "title",
        "description",
        "status",
        "priority",
        "epic_id",
        "type",
        "prompt",
        "branch_name",
        "acceptance_criteria_json",
        "success_criteria_json",
        "assumptions_json",
        "updated_at",
        "planned_at",
        "started_at",
        "completed_at",
        "blocked_by",
        "blocked_reason",
        "plan_path",
        "pr_url",
    }
)

def _validate_fields(fields: dict, allowed: frozenset) -> None:
    """Reject any field names not in the allowed set."""
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Disallowed field(s): {bad}")

class BacklogDB(BaseStore):
    """Relational store for the roadmap -> epic -> feature hierarchy.

    Receives a PixlDB instance and obtains thread-local connections
    for each operation, making it safe for multi-threaded use.
    """

    # Shared helpers

    def _record_transition(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        trigger: str | None = None,
        trigger_id: str | None = None,
    ) -> None:
        """Record a state transition row."""
        self._conn.execute(
            """INSERT INTO state_transitions
               (entity_type, entity_id, from_status, to_status, trigger, trigger_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (entity_type, entity_id, old_status, new_status, trigger, trigger_id),
        )

    def _build_update(self, table: str, entity_id: str, fields: dict[str, Any]) -> None:
        """Execute a dynamic UPDATE with the given fields."""
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [entity_id]
        self._conn.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)

    # ID generation

    def _next_id(self, entity_type: str) -> str:
        """Generate next sequential ID for an entity type.

        Thread-safe via SQLite's implicit write lock.
        """
        prefixes = {"feature": "feat", "epic": "epic", "roadmap": "roadmap"}
        prefix = prefixes[entity_type]

        row = self._conn.execute(
            "SELECT next_value FROM id_sequences WHERE name = ?",
            (entity_type,),
        ).fetchone()
        next_val = row["next_value"] if row else 1

        self._conn.execute(
            "UPDATE id_sequences SET next_value = ? WHERE name = ?",
            (next_val + 1, entity_type),
        )

        return f"{prefix}-{next_val:03d}"

    # Roadmaps

    def add_roadmap(
        self,
        title: str,
        original_prompt: str = "",
        status: str = "drafting",
    ) -> dict[str, Any]:
        """Create a new roadmap. Returns the created roadmap dict."""
        roadmap_id = self._next_id("roadmap")
        now = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO roadmaps (id, title, original_prompt, status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (roadmap_id, title, original_prompt, status, now),
        )
        self._conn.commit()
        return self.get_roadmap(roadmap_id)  # type: ignore

    def get_roadmap(self, roadmap_id: str) -> dict[str, Any] | None:
        """Get roadmap by ID with its epic_ids and milestones."""
        row = self._conn.execute("SELECT * FROM roadmaps WHERE id = ?", (roadmap_id,)).fetchone()
        if not row:
            return None

        roadmap = dict(row)

        epic_rows = self._conn.execute(
            "SELECT id FROM epics WHERE roadmap_id = ? ORDER BY created_at",
            (roadmap_id,),
        ).fetchall()
        roadmap["epic_ids"] = [r["id"] for r in epic_rows]

        ms_rows = self._conn.execute(
            "SELECT * FROM milestones WHERE roadmap_id = ? ORDER BY sort_order",
            (roadmap_id,),
        ).fetchall()
        milestones = [dict(r) for r in ms_rows]
        if milestones:
            try:
                ids = [m["id"] for m in milestones]
                placeholders = ",".join("?" for _ in ids)
                dep_rows = self._conn.execute(
                    f"""
                    SELECT milestone_id, depends_on_id
                    FROM milestone_dependencies
                    WHERE milestone_id IN ({placeholders})
                    """,
                    ids,
                ).fetchall()
                dep_map: dict[int, list[int]] = {}
                for r in dep_rows:
                    dep_map.setdefault(int(r["milestone_id"]), []).append(int(r["depends_on_id"]))
                for m in milestones:
                    m["depends_on"] = sorted(dep_map.get(int(m["id"]), []))
            except Exception:
                # Best-effort: keep roadmap reads resilient even if dependency table is unavailable.
                for m in milestones:
                    m.setdefault("depends_on", [])
        roadmap["milestones"] = milestones

        roadmap["notes"] = self._get_notes("roadmap", roadmap_id)

        return roadmap

    def update_roadmap(self, roadmap_id: str, **fields) -> bool:
        """Update roadmap fields. Returns True if found."""
        if not fields:
            return False

        fields["updated_at"] = datetime.now().isoformat()
        _validate_fields(fields, _ROADMAP_FIELDS)
        self._build_update("roadmaps", roadmap_id, fields)
        self._conn.commit()
        return True

    def update_roadmap_status(
        self,
        roadmap_id: str,
        status: str,
        note: str | None = None,
        trigger: str | None = None,
    ) -> dict[str, Any] | None:
        """Update roadmap status with transition recording."""
        current = self.get_roadmap(roadmap_id)
        if not current:
            return None

        old_status = current["status"]
        now = datetime.now().isoformat()

        updates: dict[str, Any] = {"status": status, "updated_at": now}
        if status == "completed":
            updates["completed_at"] = now

        self._build_update("roadmaps", roadmap_id, updates)
        self._record_transition("roadmap", roadmap_id, old_status, status, trigger)

        if note:
            self._add_note("roadmap", roadmap_id, note)

        self._conn.commit()
        return self.get_roadmap(roadmap_id)

    def list_roadmaps(self, status: str | None = None) -> list[dict[str, Any]]:
        """List roadmaps, optionally filtered by status."""
        if status:
            rows = self._conn.execute(
                "SELECT id FROM roadmaps WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT id FROM roadmaps ORDER BY created_at DESC").fetchall()

        return [self.get_roadmap(r["id"]) for r in rows]  # type: ignore

    def add_milestone(
        self,
        roadmap_id: str,
        name: str,
        target_date: str | None = None,
        sort_order: int = 0,
    ) -> dict[str, Any]:
        """Add a milestone to a roadmap."""
        cursor = self._conn.execute(
            """INSERT INTO milestones (roadmap_id, name, target_date, sort_order)
               VALUES (?, ?, ?, ?)""",
            (roadmap_id, name, target_date, sort_order),
        )
        self._conn.commit()

        row = self._conn.execute(
            "SELECT * FROM milestones WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    # Epics

    def add_epic(
        self,
        title: str,
        original_prompt: str = "",
        workflow_id: str | None = None,
        outcome: str = "",
        kpis: list[dict[str, Any]] | None = None,
        roadmap_id: str | None = None,
        milestone_id: int | None = None,
        status: str = "drafting",
    ) -> dict[str, Any]:
        """Create a new epic. Returns the created epic dict."""
        epic_id = self._next_id("epic")
        now = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO epics
               (id, roadmap_id, milestone_id, title, original_prompt, workflow_id, outcome, kpis_json, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                epic_id,
                roadmap_id,
                milestone_id,
                title,
                original_prompt,
                workflow_id,
                outcome,
                json.dumps(kpis or []),
                status,
                now,
            ),
        )
        self._conn.commit()
        return self.get_epic(epic_id)  # type: ignore

    def get_epic(self, epic_id: str) -> dict[str, Any] | None:
        """Get epic by ID with its feature_ids."""
        row = self._conn.execute("SELECT * FROM epics WHERE id = ?", (epic_id,)).fetchone()
        if not row:
            return None

        epic = dict(row)
        self._deserialize_json(epic, {"kpis_json": "kpis"}, defaults={"kpis": []})

        feat_rows = self._conn.execute(
            "SELECT id FROM features WHERE epic_id = ? ORDER BY created_at",
            (epic_id,),
        ).fetchall()
        epic["feature_ids"] = [r["id"] for r in feat_rows]

        epic["notes"] = self._get_notes("epic", epic_id)

        epic["progress"] = self._compute_epic_progress(epic_id)

        return epic

    def update_epic(self, epic_id: str, **fields) -> bool:
        """Update epic fields. Returns True if found."""
        if not fields:
            return False

        if "kpis" in fields:
            fields["kpis_json"] = json.dumps(fields.pop("kpis"))

        fields["updated_at"] = datetime.now().isoformat()
        _validate_fields(fields, _EPIC_FIELDS)
        self._build_update("epics", epic_id, fields)
        self._conn.commit()
        return True

    def update_epic_status(
        self,
        epic_id: str,
        status: str,
        note: str | None = None,
        trigger: str | None = None,
    ) -> dict[str, Any] | None:
        """Update epic status with transition recording."""
        current = self.get_epic(epic_id)
        if not current:
            return None

        old_status = current["status"]
        now = datetime.now().isoformat()

        updates: dict[str, Any] = {"status": status, "updated_at": now}
        if status == "completed":
            updates["completed_at"] = now

        self._build_update("epics", epic_id, updates)
        self._record_transition("epic", epic_id, old_status, status, trigger)

        if note:
            self._add_note("epic", epic_id, note)

        self._conn.commit()
        return self.get_epic(epic_id)

    def list_epics(
        self,
        status: str | None = None,
        roadmap_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List epics with optional filters."""
        where, params = self._build_where({"status": status, "roadmap_id": roadmap_id})
        rows = self._conn.execute(
            f"SELECT id FROM epics {where} ORDER BY created_at DESC", params
        ).fetchall()

        return [self.get_epic(r["id"]) for r in rows]  # type: ignore

    def _compute_epic_progress(self, epic_id: str) -> dict[str, Any]:
        """Compute progress summary for an epic from its features."""
        row = self._conn.execute(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status IN ('backlog', 'planned') THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'review' THEN 1 ELSE 0 END) as review
               FROM features WHERE epic_id = ?""",
            (epic_id,),
        ).fetchone()

        total = row["total"] or 0
        done = row["done"] or 0

        return {
            "total": total,
            "done": done,
            "in_progress": row["in_progress"] or 0,
            "review": row["review"] or 0,
            "blocked": row["blocked"] or 0,
            "failed": row["failed"] or 0,
            "pending": row["pending"] or 0,
            "percentage": round((done / total) * 100, 1) if total > 0 else 0.0,
        }

    # Features

    def add_feature(
        self,
        title: str,
        description: str = "",
        feature_type: str = "feature",
        priority: str = "P2",
        depends_on: list[str] | None = None,
        epic_id: str | None = None,
        roadmap_id: str | None = None,
        acceptance_criteria: list[str] | None = None,
        status: str = "backlog",
    ) -> dict[str, Any]:
        """Create a new feature. Returns the created feature dict."""
        if len(title) > 200:
            title = title[:197] + "..."
        feature_id = self._next_id("feature")
        now = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO features
               (id, epic_id, roadmap_id, title, description, type, priority, status, created_at, acceptance_criteria_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feature_id,
                epic_id,
                roadmap_id,
                title,
                description,
                feature_type,
                priority,
                status,
                now,
                json.dumps(acceptance_criteria or []),
            ),
        )

        if depends_on:
            for dep_id in depends_on:
                self._conn.execute(
                    """INSERT OR IGNORE INTO feature_dependencies (feature_id, depends_on_id)
                       VALUES (?, ?)""",
                    (feature_id, dep_id),
                )

        self._conn.commit()
        return self.get_feature(feature_id)  # type: ignore

    def get_feature(self, feature_id: str) -> dict[str, Any] | None:
        """Get feature by ID with dependencies and notes."""
        row = self._conn.execute("SELECT * FROM features WHERE id = ?", (feature_id,)).fetchone()
        if not row:
            return None

        feature = dict(row)

        self._deserialize_json(feature, {
            "acceptance_criteria_json": "acceptance_criteria",
            "success_criteria_json": "success_criteria",
            "assumptions_json": "assumptions",
        }, defaults={"acceptance_criteria": [], "success_criteria": [], "assumptions": []})

        dep_rows = self._conn.execute(
            "SELECT depends_on_id FROM feature_dependencies WHERE feature_id = ?",
            (feature_id,),
        ).fetchall()
        feature["depends_on"] = [r[0] for r in dep_rows]

        rdep_rows = self._conn.execute(
            "SELECT feature_id FROM feature_dependencies WHERE depends_on_id = ?",
            (feature_id,),
        ).fetchall()
        feature["depended_by"] = [r[0] for r in rdep_rows]

        feature["notes"] = self._get_notes("feature", feature_id)

        return feature

    def update_feature(self, feature_id: str, **fields) -> bool:
        """Update feature fields. Returns True if found.

        Special handling for 'depends_on' list — replaces all dependencies.
        """
        depends_on = fields.pop("depends_on", None)
        if "acceptance_criteria" in fields:
            fields["acceptance_criteria_json"] = json.dumps(fields.pop("acceptance_criteria"))
        if "success_criteria" in fields:
            fields["success_criteria_json"] = json.dumps(fields.pop("success_criteria"))
        if "assumptions" in fields:
            fields["assumptions_json"] = json.dumps(fields.pop("assumptions"))

        if fields:
            fields["updated_at"] = datetime.now().isoformat()
            _validate_fields(fields, _FEATURE_FIELDS)
            self._build_update("features", feature_id, fields)

        if depends_on is not None:
            self._conn.execute(
                "DELETE FROM feature_dependencies WHERE feature_id = ?",
                (feature_id,),
            )
            for dep_id in depends_on:
                self._conn.execute(
                    """INSERT OR IGNORE INTO feature_dependencies (feature_id, depends_on_id)
                       VALUES (?, ?)""",
                    (feature_id, dep_id),
                )

        self._conn.commit()
        return True

    def update_feature_status(
        self,
        feature_id: str,
        status: str,
        note: str | None = None,
        trigger: str | None = None,
        trigger_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Update feature status with transition recording and timestamp management."""
        current = self.get_feature(feature_id)
        if not current:
            return None

        old_status = current["status"]
        now = datetime.now().isoformat()

        updates: dict[str, Any] = {"status": status, "updated_at": now}

        # Set lifecycle timestamps
        if status == "planned":
            updates["planned_at"] = now
        elif status == "in_progress":
            updates["started_at"] = now
        elif status == "done":
            updates["completed_at"] = now

        self._build_update("features", feature_id, updates)
        self._record_transition("feature", feature_id, old_status, status, trigger, trigger_id)

        if note:
            self._add_note("feature", feature_id, note)

        self._conn.commit()

        self._propagate_status(feature_id)

        return self.get_feature(feature_id)

    def remove_feature(self, feature_id: str) -> bool:
        """Remove a feature and its dependencies."""
        cursor = self._conn.execute("DELETE FROM features WHERE id = ?", (feature_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def list_features(
        self,
        status: str | None = None,
        epic_id: str | None = None,
        roadmap_id: str | None = None,
        priority: str | None = None,
        feature_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List features with optional filters."""
        where, params = self._build_where({
            "status": status,
            "epic_id": epic_id,
            "roadmap_id": roadmap_id,
            "priority": priority,
            "type": feature_type,
        })
        rows = self._conn.execute(
            f"SELECT id FROM features {where} ORDER BY priority, created_at", params
        ).fetchall()

        return [f for f in (self.get_feature(r["id"]) for r in rows) if f is not None]

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across the entire backlog."""
        try:
            row = self._conn.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'backlog' THEN 1 ELSE 0 END) as backlog,
                    SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) as planned,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN status = 'review' THEN 1 ELSE 0 END) as review,
                    SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
                    SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(total_cost_usd) as total_cost,
                    SUM(total_tokens) as total_tokens
                   FROM features"""
            ).fetchone()
            feature_stats = dict(row) if row else {}
        except Exception:
            feature_stats = {}

        try:
            row = self._conn.execute(
                """SELECT COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                   FROM epics"""
            ).fetchone()
            epic_stats = dict(row) if row else {}
        except Exception:
            epic_stats = {}

        try:
            row = self._conn.execute(
                """SELECT COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                   FROM roadmaps"""
            ).fetchone()
            roadmap_stats = dict(row) if row else {}
        except Exception:
            roadmap_stats = {}

        return {
            "features": feature_stats,
            "epics": epic_stats,
            "roadmaps": roadmap_stats,
        }

    # Dependencies & ordering

    def get_dependency_graph(self, epic_id: str | None = None) -> dict[str, list[str]]:
        """Get the dependency graph as adjacency list.

        Returns {feature_id: [depends_on_ids]}
        """
        if epic_id:
            rows = self._conn.execute(
                """SELECT fd.feature_id, fd.depends_on_id
                   FROM feature_dependencies fd
                   JOIN features f ON fd.feature_id = f.id
                   WHERE f.epic_id = ?""",
                (epic_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT feature_id, depends_on_id FROM feature_dependencies"
            ).fetchall()

        graph: dict[str, list[str]] = {}
        for r in rows:
            graph.setdefault(r["feature_id"], []).append(r["depends_on_id"])
        return graph

    def get_execution_order(self, epic_id: str) -> list[str]:
        """Get topologically sorted feature execution order for an epic.

        Features with no unmet dependencies come first.
        Raises ValueError on dependency cycles.
        """
        features = self._conn.execute(
            "SELECT id FROM features WHERE epic_id = ?", (epic_id,)
        ).fetchall()
        feature_ids = {r["id"] for r in features}

        deps = self.get_dependency_graph(epic_id)

        # Kahn's algorithm for topological sort
        in_degree: dict[str, int] = dict.fromkeys(feature_ids, 0)
        for fid, dep_list in deps.items():
            if fid in feature_ids:
                for dep in dep_list:
                    if dep in feature_ids:
                        in_degree[fid] = in_degree.get(fid, 0) + 1

        queue = [fid for fid, deg in in_degree.items() if deg == 0]
        queue.sort()  # Deterministic ordering
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            dependents = self._conn.execute(
                """SELECT feature_id FROM feature_dependencies
                   WHERE depends_on_id = ? AND feature_id IN ({})""".format(
                    ",".join("?" for _ in feature_ids)
                ),
                (node, *feature_ids),
            ).fetchall()

            for dep_row in dependents:
                dep_id = dep_row["feature_id"]
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    queue.append(dep_id)
                    queue.sort()

        if len(result) != len(feature_ids):
            missing = feature_ids - set(result)
            raise ValueError(f"Dependency cycle detected involving: {', '.join(sorted(missing))}")

        return result

    def get_unblocked_features(self, epic_id: str | None = None) -> list[dict[str, Any]]:
        """Get features whose dependencies are all satisfied (done).

        These are the features that can be executed next.
        """
        if epic_id:
            candidates = self._conn.execute(
                """SELECT id FROM features
                   WHERE epic_id = ? AND status IN ('backlog', 'planned')""",
                (epic_id,),
            ).fetchall()
        else:
            candidates = self._conn.execute(
                "SELECT id FROM features WHERE status IN ('backlog', 'planned')"
            ).fetchall()

        unblocked = []
        for row in candidates:
            fid = row["id"]
            blocked = self._conn.execute(
                """SELECT COUNT(*) as cnt FROM feature_dependencies fd
                   JOIN features f ON fd.depends_on_id = f.id
                   WHERE fd.feature_id = ? AND f.status != 'done'""",
                (fid,),
            ).fetchone()

            if blocked["cnt"] == 0:
                feat = self.get_feature(fid)
                if feat is not None:
                    unblocked.append(feat)

        return unblocked

    def check_dependencies_met(self, feature_id: str) -> tuple[bool, list[str]]:
        """Check if all dependencies for a feature are satisfied.

        Returns (all_met, list_of_unmet_dependency_ids).
        """
        unmet = self._conn.execute(
            """SELECT fd.depends_on_id, f.status
               FROM feature_dependencies fd
               JOIN features f ON fd.depends_on_id = f.id
               WHERE fd.feature_id = ? AND f.status != 'done'""",
            (feature_id,),
        ).fetchall()

        unmet_ids = [r["depends_on_id"] for r in unmet]
        return len(unmet_ids) == 0, unmet_ids

    # Status propagation

    def _propagate_status(self, feature_id: str) -> None:
        """Propagate feature status changes upward to epic and roadmap.

        Called automatically after feature status updates.
        """
        feature = self._conn.execute(
            "SELECT epic_id, roadmap_id FROM features WHERE id = ?",
            (feature_id,),
        ).fetchone()
        if not feature:
            return

        epic_id = feature["epic_id"]
        if epic_id:
            self._propagate_epic_status(epic_id)

    def _propagate_epic_status(self, epic_id: str) -> None:
        """Recalculate epic status based on child feature states."""
        progress = self._compute_epic_progress(epic_id)
        epic = self._conn.execute("SELECT status FROM epics WHERE id = ?", (epic_id,)).fetchone()
        if not epic:
            return

        current_status = epic["status"]
        total = progress["total"]
        if total == 0:
            return

        # Determine new status
        new_status = current_status
        if progress["done"] == total:
            new_status = "completed"
        elif progress["in_progress"] > 0 or progress["review"] > 0 or progress["done"] > 0:
            new_status = "in_progress"
        elif progress["failed"] > 0 and progress["in_progress"] == 0:
            new_status = "failed"

        if new_status != current_status and current_status != "drafting":
            from pixl.state.machine import MACHINES

            machine = MACHINES.get("epic")
            if machine and not machine.is_allowed(current_status, new_status):
                return  # Guard: transition not allowed by state machine

            now = datetime.now().isoformat()
            updates: dict[str, Any] = {"status": new_status, "updated_at": now}
            if new_status == "completed":
                updates["completed_at"] = now

            self._build_update("epics", epic_id, updates)
            self._record_transition("epic", epic_id, current_status, new_status, "auto_propagation")

            epic_row = self._conn.execute(
                "SELECT roadmap_id FROM epics WHERE id = ?", (epic_id,)
            ).fetchone()
            if epic_row and epic_row["roadmap_id"]:
                self._propagate_roadmap_status(epic_row["roadmap_id"])

    def _propagate_roadmap_status(self, roadmap_id: str) -> None:
        """Recalculate roadmap status based on child epic states."""
        row = self._conn.execute(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
               FROM epics WHERE roadmap_id = ?""",
            (roadmap_id,),
        ).fetchone()

        roadmap = self._conn.execute(
            "SELECT status FROM roadmaps WHERE id = ?", (roadmap_id,)
        ).fetchone()
        if not roadmap:
            return

        current_status = roadmap["status"]
        total = row["total"] or 0
        if total == 0:
            return

        new_status = current_status
        if row["completed"] == total:
            new_status = "completed"
        elif row["in_progress"] > 0 or row["completed"] > 0:
            new_status = "in_progress"

        if new_status != current_status and current_status not in ("drafting",):
            from pixl.state.machine import MACHINES

            machine = MACHINES.get("roadmap")
            if machine and not machine.is_allowed(current_status, new_status):
                return  # Guard: transition not allowed by state machine

            now = datetime.now().isoformat()
            updates: dict[str, Any] = {"status": new_status, "updated_at": now}
            if new_status == "completed":
                updates["completed_at"] = now

            self._build_update("roadmaps", roadmap_id, updates)
            self._record_transition("roadmap", roadmap_id, current_status, new_status, "auto_propagation")

    # Notes (shared across entity types)

    def _get_notes(self, entity_type: str, entity_id: str) -> list[str]:
        """Get notes for an entity, formatted with timestamps."""
        rows = self._conn.execute(
            """SELECT content, created_at FROM notes
               WHERE entity_type = ? AND entity_id = ?
               ORDER BY created_at""",
            (entity_type, entity_id),
        ).fetchall()
        return [f"[{r['created_at']}] {r['content']}" for r in rows]

    def _add_note(self, entity_type: str, entity_id: str, content: str) -> None:
        """Add a note to an entity."""
        self._conn.execute(
            "INSERT INTO notes (entity_type, entity_id, content) VALUES (?, ?, ?)",
            (entity_type, entity_id, content),
        )

    def add_note(self, entity_type: str, entity_id: str, content: str) -> None:
        """Public method to add a note to any entity."""
        self._add_note(entity_type, entity_id, content)
        self._conn.commit()
