"""Persistence helpers for plan-only execution chains."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pixl.storage.db.base import BaseStore


class ChainPlanDB(BaseStore):
    """CRUD and validation helpers for execution chain plans."""

    def get_chain(self, chain_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT id, epic_id, source_session_id, mode, status, max_parallel, failure_policy,
                   stop_on_failure, validation_summary_json, created_at, updated_at
            FROM execution_chains
            WHERE id = ?
            """,
            (chain_id,),
        ).fetchone()
        if not row:
            return None
        chain = dict(row)
        chain["stop_on_failure"] = bool(chain.get("stop_on_failure"))
        chain["validation_summary"] = _parse_validation(chain.pop("validation_summary_json", "{}"))
        return chain

    def get_chain_by_epic(self, epic_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT id
            FROM execution_chains
            WHERE epic_id = ?
            """,
            (epic_id,),
        ).fetchone()
        if not row:
            return None
        return self.get_chain(str(row["id"]))

    def list_chains(self) -> list[dict[str, Any]]:
        """List chains with lightweight node status counts."""
        rows = self._conn.execute(
            """
            SELECT
                c.id,
                c.epic_id,
                c.source_session_id,
                c.mode,
                c.status,
                c.max_parallel,
                c.failure_policy,
                c.stop_on_failure,
                c.validation_summary_json,
                c.created_at,
                c.updated_at,
                COUNT(n.node_id) AS total_nodes,
                SUM(CASE WHEN n.status = 'pending' THEN 1 ELSE 0 END) AS pending_nodes,
                SUM(CASE WHEN n.status = 'running' THEN 1 ELSE 0 END) AS running_nodes,
                SUM(CASE WHEN n.status = 'completed' THEN 1 ELSE 0 END) AS completed_nodes,
                SUM(CASE WHEN n.status = 'failed' THEN 1 ELSE 0 END) AS failed_nodes,
                SUM(CASE WHEN n.status = 'blocked' THEN 1 ELSE 0 END) AS blocked_nodes,
                SUM(CASE WHEN n.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_nodes
            FROM execution_chains c
            LEFT JOIN execution_chain_nodes n ON n.chain_id = c.id
            GROUP BY c.id
            ORDER BY COALESCE(c.updated_at, c.created_at) DESC, c.id ASC
            """
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            chain = dict(row)
            chain["stop_on_failure"] = bool(chain.get("stop_on_failure"))
            chain["validation_summary"] = _parse_validation(
                chain.pop("validation_summary_json", "{}")
            )
            chain["node_counts"] = {
                "total": int(chain.pop("total_nodes") or 0),
                "pending": int(chain.pop("pending_nodes") or 0),
                "running": int(chain.pop("running_nodes") or 0),
                "completed": int(chain.pop("completed_nodes") or 0),
                "failed": int(chain.pop("failed_nodes") or 0),
                "blocked": int(chain.pop("blocked_nodes") or 0),
                "cancelled": int(chain.pop("cancelled_nodes") or 0),
            }
            results.append(chain)
        return results

    def get_nodes(self, chain_id: str, *, include_execution: bool = False) -> list[dict[str, Any]]:
        """Return chain nodes, optionally including execution/runtime columns."""
        if include_execution:
            cols = """chain_id, node_id, feature_id, feature_ref, wave, parallel_group,
                   owner, risk_class, estimate_points,
                   status, session_id, attempt_count, started_at, completed_at, error,
                   metadata_json"""
        else:
            cols = """chain_id, node_id, feature_id, feature_ref, wave, parallel_group,
                   owner, risk_class, estimate_points, metadata_json"""
        rows = self._conn.execute(
            f"""
            SELECT {cols}
            FROM execution_chain_nodes
            WHERE chain_id = ?
            ORDER BY wave ASC, parallel_group ASC, node_id ASC
            """,
            (chain_id,),
        ).fetchall()
        nodes: list[dict[str, Any]] = []
        for row in rows:
            node = dict(row)
            node["metadata"] = _parse_json_dict(node.pop("metadata_json", "{}"))
            nodes.append(node)
        return nodes

    def get_execution_nodes(self, chain_id: str) -> list[dict[str, Any]]:
        """Return chain nodes including execution/runtime columns."""
        return self.get_nodes(chain_id, include_execution=True)

    def get_edges(self, chain_id: str) -> list[dict[str, str]]:
        rows = self._conn.execute(
            """
            SELECT from_node_id, to_node_id
            FROM execution_chain_edges
            WHERE chain_id = ?
            ORDER BY from_node_id ASC, to_node_id ASC
            """,
            (chain_id,),
        ).fetchall()
        return [{"from": str(r["from_node_id"]), "to": str(r["to_node_id"])} for r in rows]

    def get_chain_detail(self, chain_id: str) -> dict[str, Any] | None:
        """Return chain + plan + execution node details (single payload)."""
        chain = self.get_chain(chain_id)
        if chain is None:
            return None
        edges = self.get_edges(chain_id)
        nodes = self.get_execution_nodes(chain_id)

        waves: list[list[dict[str, Any]]] = []
        wave_map: dict[int, list[dict[str, Any]]] = {}
        for node in nodes:
            wave_map.setdefault(int(node.get("wave", 0) or 0), []).append(node)
        for wave in sorted(wave_map):
            waves.append(wave_map[wave])

        return {
            "chain_id": chain["id"],
            "epic_id": chain["epic_id"],
            "mode": chain["mode"],
            "status": chain["status"],
            "max_parallel": chain["max_parallel"],
            "failure_policy": chain["failure_policy"],
            "stop_on_failure": chain["stop_on_failure"],
            "validation_summary": chain["validation_summary"],
            "nodes": nodes,
            "edges": edges,
            "waves": waves,
            "created_at": chain.get("created_at"),
            "updated_at": chain.get("updated_at"),
        }

    def set_chain_status(self, chain_id: str, status: str) -> None:
        self._conn.execute(
            """
            UPDATE execution_chains
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, datetime.now().isoformat(), chain_id),
        )
        self._conn.commit()

    def configure_chain_execution(
        self,
        chain_id: str,
        *,
        max_parallel: int | None = None,
        stop_on_failure: bool | None = None,
    ) -> None:
        """Update execution policy fields on a chain."""
        updates: list[str] = []
        values: list[Any] = []
        if max_parallel is not None:
            if int(max_parallel) <= 0:
                raise ValueError("max_parallel must be > 0")
            updates.append("max_parallel = ?")
            values.append(int(max_parallel))
        if stop_on_failure is not None:
            updates.append("stop_on_failure = ?")
            values.append(1 if bool(stop_on_failure) else 0)
        if not updates:
            return
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(chain_id)
        self._conn.execute(
            f"UPDATE execution_chains SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        self._conn.commit()

    def get_plan(self, chain_id: str) -> dict[str, Any] | None:
        chain = self.get_chain(chain_id)
        if chain is None:
            return None
        nodes = self.get_nodes(chain_id)
        edges = self.get_edges(chain_id)
        waves: list[list[str]] = []
        wave_map: dict[int, list[str]] = {}
        for node in nodes:
            wave = int(node.get("wave", 0))
            wave_map.setdefault(wave, []).append(str(node.get("feature_ref", "")))
        for wave in sorted(wave_map):
            waves.append(wave_map[wave])
        return {
            "chain_id": chain["id"],
            "epic_id": chain["epic_id"],
            "mode": chain["mode"],
            "status": chain["status"],
            "max_parallel": chain["max_parallel"],
            "failure_policy": chain["failure_policy"],
            "stop_on_failure": chain["stop_on_failure"],
            "validation_summary": chain["validation_summary"],
            "nodes": nodes,
            "edges": edges,
            "waves": waves,
        }

    def try_claim_node_for_execution(
        self,
        chain_id: str,
        node_id: str,
        *,
        session_id: str,
    ) -> bool:
        """Atomically claim a pending node for execution.

        Returns True if the node was claimed (status transitioned pending -> running).
        """
        now = datetime.now().isoformat()
        cursor = self._conn.execute(
            """
            UPDATE execution_chain_nodes
            SET status = 'running',
                session_id = ?,
                attempt_count = COALESCE(attempt_count, 0) + 1,
                started_at = COALESCE(started_at, ?),
                completed_at = NULL,
                error = NULL
            WHERE chain_id = ?
              AND node_id = ?
              AND status = 'pending'
            """,
            (session_id, now, chain_id, node_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def set_node_error(self, chain_id: str, node_id: str, *, error: str | None) -> None:
        """Set a human-visible error/blocked reason without changing node status."""
        self._conn.execute(
            """
            UPDATE execution_chain_nodes
            SET error = ?
            WHERE chain_id = ?
              AND node_id = ?
            """,
            (error, chain_id, node_id),
        )
        self._conn.commit()

    def update_node_metadata(
        self,
        chain_id: str,
        node_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge updates into metadata_json and return the new metadata."""
        row = self._conn.execute(
            """
            SELECT metadata_json
            FROM execution_chain_nodes
            WHERE chain_id = ?
              AND node_id = ?
            """,
            (chain_id, node_id),
        ).fetchone()
        current = _parse_json_dict(row["metadata_json"] if row else "{}")
        current.update(updates or {})
        self._conn.execute(
            """
            UPDATE execution_chain_nodes
            SET metadata_json = ?
            WHERE chain_id = ?
              AND node_id = ?
            """,
            (json.dumps(current, sort_keys=True), chain_id, node_id),
        )
        self._conn.commit()
        return current

    def mark_node_completed(self, chain_id: str, node_id: str) -> None:
        self._conn.execute(
            """
            UPDATE execution_chain_nodes
            SET status = 'completed',
                completed_at = ?
            WHERE chain_id = ?
              AND node_id = ?
            """,
            (datetime.now().isoformat(), chain_id, node_id),
        )
        self._conn.commit()

    def mark_node_failed(self, chain_id: str, node_id: str, *, error: str | None) -> None:
        self._conn.execute(
            """
            UPDATE execution_chain_nodes
            SET status = 'failed',
                completed_at = ?,
                error = ?
            WHERE chain_id = ?
              AND node_id = ?
            """,
            (datetime.now().isoformat(), error, chain_id, node_id),
        )
        self._conn.commit()

    def mark_nodes_blocked(
        self,
        chain_id: str,
        node_ids: list[str],
        *,
        reason: str | None = None,
    ) -> None:
        if not node_ids:
            return
        now = datetime.now().isoformat()
        for node_id in node_ids:
            self._conn.execute(
                """
                UPDATE execution_chain_nodes
                SET status = 'blocked',
                    completed_at = COALESCE(completed_at, ?),
                    error = COALESCE(error, ?)
                WHERE chain_id = ?
                  AND node_id = ?
                  AND status = 'pending'
                """,
                (now, reason, chain_id, node_id),
            )
        self._conn.commit()

    def mark_nodes_cancelled(
        self,
        chain_id: str,
        node_ids: list[str],
        *,
        reason: str | None = None,
    ) -> None:
        """Mark nodes as cancelled (best-effort visibility)."""
        if not node_ids:
            return
        now = datetime.now().isoformat()
        for node_id in node_ids:
            self._conn.execute(
                """
                UPDATE execution_chain_nodes
                SET status = 'cancelled',
                    completed_at = COALESCE(completed_at, ?),
                    error = COALESCE(error, ?)
                WHERE chain_id = ?
                  AND node_id = ?
                  AND status IN ('pending', 'running')
                """,
                (now, reason, chain_id, node_id),
            )
        self._conn.commit()

    def patch_plan(
        self,
        chain_id: str,
        *,
        max_parallel: int | None = None,
        node_updates: list[dict[str, Any]] | None = None,
        edges: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        chain = self.get_chain(chain_id)
        if chain is None:
            raise ValueError(f"Chain not found: {chain_id}")

        nodes = self.get_nodes(chain_id)
        node_ids = {str(node["node_id"]) for node in nodes}
        node_by_id = {str(node["node_id"]): node for node in nodes}
        node_ids_by_ref = {str(node["feature_ref"]): str(node["node_id"]) for node in nodes}
        existing_edges = {(edge["from"], edge["to"]) for edge in self.get_edges(chain_id)}

        update_by_node: dict[str, dict[str, Any]] = {}
        for raw in node_updates or []:
            node_id = _resolve_node_id(
                node_ref=raw.get("node_id"),
                feature_ref=raw.get("feature_ref"),
                node_ids=node_ids,
                node_ids_by_ref=node_ids_by_ref,
            )
            if node_id is None:
                raise ValueError("Node update requires a valid node_id or feature_ref")

            updates: dict[str, Any] = {}
            for field in ("wave", "parallel_group", "owner", "risk_class", "estimate_points"):
                if field in raw and raw[field] is not None:
                    updates[field] = raw[field]
            if not updates:
                continue

            if "wave" in updates and int(updates["wave"]) < 0:
                raise ValueError("wave must be >= 0")
            if "parallel_group" in updates and int(updates["parallel_group"]) < 0:
                raise ValueError("parallel_group must be >= 0")
            if "estimate_points" in updates and int(updates["estimate_points"]) <= 0:
                raise ValueError("estimate_points must be > 0")
            if "risk_class" in updates and updates["risk_class"] not in {
                "low",
                "medium",
                "high",
                "critical",
            }:
                raise ValueError("risk_class must be one of low|medium|high|critical")

            update_by_node.setdefault(node_id, {}).update(updates)

            if "suggested_workflow" in raw and raw["suggested_workflow"] is not None:
                valid_workflows = {"tdd", "simple", "debug"}
                if raw["suggested_workflow"] not in valid_workflows:
                    raise ValueError(f"suggested_workflow must be one of {sorted(valid_workflows)}")
                self.update_node_metadata(
                    chain_id, node_id, updates={"suggested_workflow": raw["suggested_workflow"]}
                )

        if edges is None:
            requested_edges: set[tuple[str, str]] = set(existing_edges)
        else:
            requested_edges = set()
            for edge in edges:
                src = _resolve_node_id(
                    node_ref=edge.get("from"),
                    feature_ref=edge.get("from"),
                    node_ids=node_ids,
                    node_ids_by_ref=node_ids_by_ref,
                )
                dst = _resolve_node_id(
                    node_ref=edge.get("to"),
                    feature_ref=edge.get("to"),
                    node_ids=node_ids,
                    node_ids_by_ref=node_ids_by_ref,
                )
                if src is None or dst is None:
                    raise ValueError("All edge endpoints must reference known nodes")
                requested_edges.add((src, dst))

            removed_required_edges = existing_edges - requested_edges
            if removed_required_edges:
                raise ValueError("Cannot remove required dependency edges")

        cycles, dangling_refs, _orphan_nodes = _analyze_graph(
            node_ids=node_ids,
            edges=requested_edges,
        )
        if dangling_refs:
            raise ValueError(f"Dangling edges detected: {sorted(dangling_refs)}")
        if cycles:
            raise ValueError(f"Cycle detected: {cycles}")

        temp_waves = {str(node["node_id"]): int(node.get("wave", 0)) for node in nodes}
        for node_id, updates in update_by_node.items():
            if "wave" in updates:
                temp_waves[node_id] = int(updates["wave"])

        for src, dst in sorted(requested_edges):
            if temp_waves[src] >= temp_waves[dst]:
                raise ValueError(
                    f"Dependency-safe ordering violated: node '{src}' must be in an earlier wave than '{dst}'"
                )

        now = datetime.now().isoformat()
        if max_parallel is not None:
            if int(max_parallel) <= 0:
                raise ValueError("max_parallel must be > 0")
            self._conn.execute(
                """
                UPDATE execution_chains
                SET max_parallel = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(max_parallel), now, chain_id),
            )

        for node_id, updates in update_by_node.items():
            set_parts: list[str] = []
            values: list[Any] = []
            for key, value in updates.items():
                set_parts.append(f"{key} = ?")
                if key in {"wave", "parallel_group", "estimate_points"}:
                    values.append(int(value))
                else:
                    values.append(value)
            if set_parts:
                values.extend([chain_id, node_id])
                self._conn.execute(
                    f"""
                    UPDATE execution_chain_nodes
                    SET {", ".join(set_parts)}
                    WHERE chain_id = ? AND node_id = ?
                    """,
                    values,
                )

            node = node_by_id.get(node_id, {})
            feature_id = node.get("feature_id")
            feature_set: list[str] = []
            feature_values: list[Any] = []
            for field in ("owner", "risk_class", "estimate_points"):
                if field in updates:
                    feature_set.append(f"{field} = ?")
                    if field == "estimate_points":
                        feature_values.append(int(updates[field]))
                    else:
                        feature_values.append(updates[field])
            if feature_id and feature_set:
                feature_set.append("updated_at = ?")
                feature_values.extend([now, feature_id])
                self._conn.execute(
                    f"""
                    UPDATE features
                    SET {", ".join(feature_set)}
                    WHERE id = ?
                    """,
                    feature_values,
                )

        if edges is not None:
            self._conn.execute("DELETE FROM execution_chain_edges WHERE chain_id = ?", (chain_id,))
            for src, dst in sorted(requested_edges):
                self._conn.execute(
                    """
                    INSERT INTO execution_chain_edges
                        (chain_id, from_node_id, to_node_id)
                    VALUES (?, ?, ?)
                    """,
                    (chain_id, src, dst),
                )

        self._conn.commit()
        return self.validate_chain(chain_id)

    def validate_chain(self, chain_id: str) -> dict[str, Any]:
        chain = self.get_chain(chain_id)
        if chain is None:
            raise ValueError(f"Chain not found: {chain_id}")

        nodes = self.get_nodes(chain_id)
        edges = self.get_edges(chain_id)
        node_ids = {str(node["node_id"]) for node in nodes}
        edge_pairs = {(edge["from"], edge["to"]) for edge in edges}

        cycle_nodes, dangling_refs, orphan_nodes = _analyze_graph(
            node_ids=node_ids, edges=edge_pairs
        )

        notes: list[str] = []
        if cycle_nodes:
            notes.append("cycles_detected")
        if dangling_refs:
            notes.append("dangling_edges")
        if orphan_nodes:
            notes.append("orphan_nodes_detected")

        validation_summary = {
            "dag_valid": not cycle_nodes and not dangling_refs,
            "cycles_detected": cycle_nodes,
            "orphan_nodes": orphan_nodes,
            "notes": notes,
        }

        status = chain["status"]
        if status in {"plan_draft", "plan_ready"}:
            status = "plan_ready" if validation_summary["dag_valid"] else "plan_draft"

        self._conn.execute(
            """
            UPDATE execution_chains
            SET status = ?, validation_summary_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(validation_summary, sort_keys=True),
                datetime.now().isoformat(),
                chain_id,
            ),
        )
        self._conn.commit()
        return self.get_plan(chain_id) or {}

    def start_chain(self, chain_id: str) -> dict[str, Any]:
        chain = self.get_chain(chain_id)
        if chain is None:
            raise ValueError(f"Chain not found: {chain_id}")
        if chain.get("status") != "plan_ready":
            raise ValueError("Chain must be plan_ready before start")

        self._conn.execute(
            """
            UPDATE execution_chains
            SET status = 'running', updated_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), chain_id),
        )
        self._conn.commit()
        return self.get_plan(chain_id) or {}

    def pause_chain(self, chain_id: str) -> dict[str, Any]:
        chain = self.get_chain(chain_id)
        if chain is None:
            raise ValueError(f"Chain not found: {chain_id}")
        if chain.get("status") != "running":
            raise ValueError("Chain must be running to pause")

        self._conn.execute(
            """
            UPDATE execution_chains
            SET status = 'paused', updated_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), chain_id),
        )
        self._conn.commit()
        return self.get_chain(chain_id) or {}

    def resume_chain(self, chain_id: str) -> dict[str, Any]:
        chain = self.get_chain(chain_id)
        if chain is None:
            raise ValueError(f"Chain not found: {chain_id}")
        if chain.get("status") != "paused":
            raise ValueError("Chain must be paused to resume")

        self._conn.execute(
            """
            UPDATE execution_chains
            SET status = 'running', updated_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), chain_id),
        )
        self._conn.commit()
        return self.get_chain(chain_id) or {}

    def cancel_chain(self, chain_id: str, *, reason: str | None = None) -> dict[str, Any]:
        chain = self.get_chain(chain_id)
        if chain is None:
            raise ValueError(f"Chain not found: {chain_id}")
        status = str(chain.get("status") or "")
        if status in {"completed", "failed", "cancelled"}:
            raise ValueError(f"Chain is already terminal: {status}")

        now = datetime.now().isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE execution_chains
                SET status = 'cancelled', updated_at = ?
                WHERE id = ?
                """,
                (now, chain_id),
            )
            self._conn.execute(
                """
                UPDATE execution_chain_nodes
                SET status = 'cancelled',
                    completed_at = COALESCE(completed_at, ?),
                    error = COALESCE(error, ?)
                WHERE chain_id = ?
                  AND status IN ('pending', 'running')
                """,
                (now, reason or "cancelled", chain_id),
            )
        return self.get_chain(chain_id) or {}

    def reset_chain(self, chain_id: str) -> dict[str, Any]:
        """Reset a terminal chain back to plan_ready so it can be re-run.

        Only works on failed/cancelled chains.  Preserves completed nodes.

        Smart behaviour: nodes whose workflow session completed but failed at
        the PR phase keep their ``session_id`` and get a ``pr_retry`` metadata
        flag so the chain runner can skip straight to the PR step.  All other
        non-completed nodes are fully reset (session_id cleared).

        A node is eligible for PR-retry preservation only when ALL of:
        - node has a ``session_id``
        - the session row exists in the DB
        - the session's computed status is exactly ``completed``
        - the node error is a PR-phase error OR metadata indicates session
          completed
        - the node has a ``feature_id`` (required for the PR path)

        Otherwise the node is fully reset and retry metadata is scrubbed.
        """
        chain = self.get_chain(chain_id)
        if chain is None:
            raise ValueError(f"Chain not found: {chain_id}")
        status = str(chain.get("status") or "")
        if status not in {"failed", "cancelled"}:
            raise ValueError(f"Can only reset failed/cancelled chains, got: {status}")

        now = datetime.now().isoformat()

        # Classify non-completed nodes into PR-retry vs full-reset.
        nodes = self.get_execution_nodes(chain_id)
        pr_retry_ids: list[str] = []
        full_reset_ids: list[str] = []

        for node in nodes:
            node_status = str(node.get("status") or "")
            if node_status in {"completed", "refined"}:
                continue  # already done

            node_id = str(node.get("node_id") or "")
            session_id = node.get("session_id")
            error = node.get("error")
            meta = node.get("metadata") or {}
            feature_id = node.get("feature_id")

            # Candidate for PR retry: has a session AND (error is PR-phase
            # OR metadata says session_completed).
            if (
                session_id
                and feature_id
                and (_is_pr_phase_error(error) or meta.get("session_completed"))
            ):
                session_row = self._db.sessions.get_session(str(session_id))
                s_status = str((session_row or {}).get("status", ""))
                if session_row and s_status == "completed":
                    pr_retry_ids.append(node_id)
                    continue
                # Session missing or not completed — fall through to full reset
                # even if metadata claimed session_completed.

            full_reset_ids.append(node_id)

        # Metadata keys that must be scrubbed on full reset to prevent stale
        # state from leaking into subsequent runs.
        _retry_meta_keys = (
            "pr_retry",
            "pr_retry_at",
            "session_completed",
            "awaiting_pr_merge",
            "auto_merge_requested",
            "auto_merge_requested_at",
            "auto_merge_decision",
        )

        with self._conn:
            # 1. Chain → plan_ready
            self._conn.execute(
                "UPDATE execution_chains SET status = 'plan_ready', updated_at = ? WHERE id = ?",
                (now, chain_id),
            )

            # 2. PR-retry nodes: preserve session_id, mark for PR retry.
            for nid in pr_retry_ids:
                row = self._conn.execute(
                    "SELECT metadata_json FROM execution_chain_nodes "
                    "WHERE chain_id = ? AND node_id = ?",
                    (chain_id, nid),
                ).fetchone()
                cur_meta = _parse_json_dict(row["metadata_json"] if row else "{}")
                cur_meta["pr_retry"] = True
                cur_meta["session_completed"] = True
                self._conn.execute(
                    """
                    UPDATE execution_chain_nodes
                    SET status = 'pending',
                        error = NULL,
                        completed_at = NULL,
                        metadata_json = ?
                    WHERE chain_id = ? AND node_id = ?
                    """,
                    (json.dumps(cur_meta, sort_keys=True), chain_id, nid),
                )

            # 3. Full-reset nodes: clear everything including retry metadata.
            for nid in full_reset_ids:
                row = self._conn.execute(
                    "SELECT metadata_json FROM execution_chain_nodes "
                    "WHERE chain_id = ? AND node_id = ?",
                    (chain_id, nid),
                ).fetchone()
                cur_meta = _parse_json_dict(row["metadata_json"] if row else "{}")
                # Scrub retry-related metadata keys
                dirty = False
                for key in _retry_meta_keys:
                    if key in cur_meta:
                        del cur_meta[key]
                        dirty = True
                meta_json = (
                    json.dumps(cur_meta, sort_keys=True)
                    if dirty
                    else (row["metadata_json"] if row else "{}")
                )
                self._conn.execute(
                    """
                    UPDATE execution_chain_nodes
                    SET status = 'pending',
                        error = NULL,
                        started_at = NULL,
                        completed_at = NULL,
                        session_id = NULL,
                        attempt_count = 0,
                        metadata_json = ?
                    WHERE chain_id = ? AND node_id = ?
                    """,
                    (meta_json, chain_id, nid),
                )

        self._conn.commit()
        return self.get_chain(chain_id) or {}


def _resolve_node_id(
    *,
    node_ref: str | None,
    feature_ref: str | None,
    node_ids: set[str],
    node_ids_by_ref: dict[str, str],
) -> str | None:
    if isinstance(node_ref, str) and node_ref in node_ids:
        return node_ref
    if isinstance(feature_ref, str) and feature_ref in node_ids_by_ref:
        return node_ids_by_ref[feature_ref]
    return None


_PR_PHASE_ERROR_PREFIXES = (
    "pr_automation_failed:",
    "pr_closed:",
    "pr_merge_blocked:",
    "pr_merge_",
    "pr_merge_request_failed:",
    "awaiting_pr_merge",
    "missing_base_branch",
    "missing_feature_id",
)


def _is_pr_phase_error(error: str | None) -> bool:
    """Return True if the error indicates a PR-phase failure (not a session failure)."""
    if not error:
        return False
    return any(error.startswith(p) for p in _PR_PHASE_ERROR_PREFIXES)


_parse_json_dict = BaseStore._parse_json_dict


def _parse_validation(value: str | None) -> dict[str, Any]:
    parsed = _parse_json_dict(value)
    return {
        "dag_valid": bool(parsed.get("dag_valid", False)),
        "cycles_detected": list(parsed.get("cycles_detected", [])),
        "orphan_nodes": list(parsed.get("orphan_nodes", [])),
        "notes": list(parsed.get("notes", [])),
    }


def _analyze_graph(
    *,
    node_ids: set[str],
    edges: set[tuple[str, str]],
) -> tuple[list[str], list[str], list[str]]:
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    indegree: dict[str, int] = dict.fromkeys(node_ids, 0)
    outdegree: dict[str, int] = dict.fromkeys(node_ids, 0)
    dangling_refs: set[str] = set()

    for src, dst in sorted(edges):
        if src not in node_ids or dst not in node_ids:
            dangling_refs.add(f"{src}->{dst}")
            continue
        adjacency[src].add(dst)
        indegree[dst] += 1
        outdegree[src] += 1

    cycle_nodes = _detect_cycle_nodes(adjacency)
    orphan_nodes = sorted(
        node_id
        for node_id in node_ids
        if indegree.get(node_id, 0) == 0 and outdegree.get(node_id, 0) == 0
    )
    return cycle_nodes, sorted(dangling_refs), orphan_nodes


def _detect_cycle_nodes(adjacency: dict[str, set[str]]) -> list[str]:
    color: dict[str, int] = dict.fromkeys(adjacency, 0)
    path: list[str] = []
    cycle_nodes: set[str] = set()

    def dfs(node: str) -> None:
        color[node] = 1
        path.append(node)
        for child in sorted(adjacency.get(node, set())):
            if color.get(child, 0) == 0:
                dfs(child)
            elif color.get(child) == 1:
                idx = path.index(child)
                cycle_nodes.update(path[idx:])
        path.pop()
        color[node] = 2

    for node in sorted(adjacency):
        if color[node] == 0:
            dfs(node)
    return sorted(cycle_nodes)
