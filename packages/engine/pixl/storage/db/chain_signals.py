"""Chain signal storage for inter-agent communication within swarm execution.

Agents in the same execution chain post structured signals that siblings
can query before touching shared boundaries.  WAL mode guarantees readers
never block, making this safe for parallel agent dispatch.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from pixl.storage.db.base import BaseStore

_VALID_SIGNAL_TYPES = frozenset(
    {
        "file_modified",
        "api_changed",
        "blocker",
        "discovery",
        "status_update",
        "file_claim",
        "judge_finding",
    }
)

class ChainSignalDB(BaseStore):
    """CRUD helpers for chain inter-node signals."""

    def emit_signal(
        self,
        chain_id: str,
        from_node: str,
        signal_type: str,
        payload: dict[str, Any] | None = None,
    ) -> int:
        """Insert a signal and return its row ID."""
        if signal_type not in _VALID_SIGNAL_TYPES:
            msg = f"invalid signal_type: {signal_type}"
            raise ValueError(msg)
        payload_json = json.dumps(payload or {}, default=str)
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO chain_signals (chain_id, from_node, signal_type, payload)"
                " VALUES (?, ?, ?, ?)",
                (chain_id, from_node, signal_type, payload_json),
            )
            return cur.lastrowid or 0

    def get_signals(
        self,
        chain_id: str,
        *,
        signal_type: str | None = None,
        since: str | None = None,
        exclude_node: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read signals for a chain with optional filters."""
        clauses = ["chain_id = ?"]
        params: list[Any] = [chain_id]
        if signal_type:
            clauses.append("signal_type = ?")
            params.append(signal_type)
        if since:
            clauses.append("created_at > ?")
            params.append(since)
        if exclude_node:
            clauses.append("from_node != ?")
            params.append(exclude_node)
        params.append(limit)
        sql = (
            "SELECT id, chain_id, from_node, signal_type, payload, created_at"
            " FROM chain_signals"
            f" WHERE {' AND '.join(clauses)}"
            " ORDER BY created_at DESC LIMIT ?"
        )
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_sibling_signals(
        self,
        chain_id: str,
        node_id: str,
        *,
        signal_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get signals from other nodes in the same chain."""
        clauses = ["chain_id = ?", "from_node != ?"]
        params: list[Any] = [chain_id, node_id]
        if signal_types:
            placeholders = ", ".join("?" for _ in signal_types)
            clauses.append(f"signal_type IN ({placeholders})")
            params.extend(signal_types)
        sql = (
            "SELECT id, chain_id, from_node, signal_type, payload, created_at"
            " FROM chain_signals"
            f" WHERE {' AND '.join(clauses)}"
            " ORDER BY created_at DESC LIMIT 50"
        )
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def search_signals(
        self,
        chain_id: str,
        query: str,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """FTS5 BM25 search over signal payloads."""
        sql = (
            "SELECT s.id, s.chain_id, s.from_node, s.signal_type, s.payload, s.created_at,"
            "       bm25(chain_signals_fts, 2.0, 1.0) AS score"
            " FROM chain_signals_fts fts"
            " JOIN chain_signals s ON s.rowid = fts.rowid"
            " WHERE chain_signals_fts MATCH ? AND s.chain_id = ?"
            " ORDER BY score LIMIT ?"
        )
        rows = self._conn.execute(sql, (query, chain_id, limit)).fetchall()
        return [
            {
                "id": r[0],
                "chain_id": r[1],
                "from_node": r[2],
                "signal_type": r[3],
                "payload": _parse_json(r[4]),
                "created_at": r[5],
                "score": r[6],
            }
            for r in rows
        ]

    def get_file_claims(
        self,
        chain_id: str,
        *,
        wave: int | None = None,
    ) -> dict[str, list[str]]:
        """Return {file_path: [claiming_node_ids]} from file_claim signals."""
        sql = (
            "SELECT from_node, payload FROM chain_signals"
            " WHERE chain_id = ? AND signal_type = 'file_claim'"
            " ORDER BY created_at"
        )
        rows = self._conn.execute(sql, (chain_id,)).fetchall()
        claims: dict[str, list[str]] = {}
        for row in rows:
            node_id = row[0]
            payload = _parse_json(row[1])
            files = payload.get("files", [])
            if isinstance(files, list):
                for f in files:
                    claims.setdefault(str(f), []).append(node_id)
        return claims

    def delete_signals_for_chain(self, chain_id: str) -> int:
        """Bulk delete all signals for a chain.  Returns count deleted."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM chain_signals WHERE chain_id = ?",
                (chain_id,),
            )
            return cur.rowcount

# Helpers

def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "chain_id": row[1],
        "from_node": row[2],
        "signal_type": row[3],
        "payload": _parse_json(row[4]),
        "created_at": row[5],
    }

def _parse_json(raw: str | None) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
