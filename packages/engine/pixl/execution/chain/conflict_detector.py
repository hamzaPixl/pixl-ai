"""File conflict detection and signal emission for chain nodes."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)


def filter_conflicting_nodes(
    db: PixlDB,
    chain_id: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter out candidates that overlap on files with already-running nodes.

    Only the first candidate claiming a file is dispatched; others are deferred.
    """
    if len(candidates) <= 1:
        return candidates

    existing_claims = db.chain_signals.get_file_claims(chain_id)
    running_files: set[str] = set()
    for filepath, _claiming_nodes in existing_claims.items():
        running_files.add(filepath)

    dispatched: list[dict[str, Any]] = []
    dispatched_files: set[str] = set()

    for candidate in candidates:
        meta = candidate.get("metadata") or {}
        work_scope = meta.get("work_scope") or {}

        # Estimate files from work_scope or feature description
        candidate_files: set[str] = set()
        scope_files = work_scope.get("files") or work_scope.get("files_modified") or []
        if isinstance(scope_files, list):
            candidate_files.update(str(f) for f in scope_files)

        # Check for overlap with running nodes or already-dispatched candidates
        overlap = candidate_files & (running_files | dispatched_files)
        if overlap:
            logger.info(
                "Deferring node %s (chain %s): file overlap %s",
                candidate.get("node_id"),
                chain_id,
                sorted(overlap)[:5],
            )
            continue

        dispatched.append(candidate)
        dispatched_files.update(candidate_files)

    return dispatched if dispatched else candidates[:1]


def emit_file_claims(
    db: PixlDB,
    chain_id: str,
    node_id: str,
    feature: dict[str, Any],
) -> None:
    """Emit file_claim signals for a dispatched node."""
    try:
        meta = feature.get("metadata") or {}
        work_scope = meta.get("work_scope") or {}
        files = work_scope.get("files") or work_scope.get("files_modified") or []
        if isinstance(files, list) and files:
            db.chain_signals.emit_signal(
                chain_id,
                node_id,
                "file_claim",
                {"files": [str(f) for f in files[:50]]},
            )
    except Exception:
        logger.debug("Non-critical: file claim emission failed for node %s", node_id, exc_info=True)


def extract_and_persist_signals(
    db: PixlDB,
    chain_id: str,
    node_id: str,
    session_id: str,
) -> None:
    """Read completed session baton and emit signals for sibling awareness.

    Emits:
    - ``file_modified`` per file listed in ``work_scope.files_modified``
    - ``status_update`` with node summary from baton ``current_state``
    """
    try:
        session_row = db.sessions.get_session(session_id)
        if not session_row:
            return
        baton_raw = session_row.get("baton")
        if not baton_raw:
            return
        baton = json.loads(baton_raw) if isinstance(baton_raw, str) else baton_raw
        if not isinstance(baton, dict):
            return

        work_scope = baton.get("work_scope") or {}
        files = work_scope.get("files_modified") or work_scope.get("files_touched") or []
        if isinstance(files, list) and files:
            db.chain_signals.emit_signal(
                chain_id,
                node_id,
                "file_modified",
                {"files": files[:50]},
            )

        current_state = baton.get("current_state") or ""
        summary = str(current_state)[:500] if current_state else ""
        db.chain_signals.emit_signal(
            chain_id,
            node_id,
            "status_update",
            {"summary": summary, "session_id": session_id},
        )
    except Exception:
        logger.debug("Signal extraction failed for node %s", node_id, exc_info=True)


def refresh_file_claims_from_session(
    db: PixlDB,
    chain_id: str,
    node_id: str,
    session_id: str,
) -> None:
    """Read a running session's baton work_scope and emit updated file_claim signals.

    Called during the reconciliation loop for running nodes so that file
    claims stay up-to-date as agents discover new files to modify.
    """
    try:
        session_row = db.sessions.get_session(session_id)
        if not session_row:
            return
        baton_raw = session_row.get("baton")
        if not baton_raw:
            return
        baton = json.loads(baton_raw) if isinstance(baton_raw, str) else baton_raw
        if not isinstance(baton, dict):
            return

        # work_scope may be a list of strings (file paths) or a dict with files key
        work_scope = baton.get("work_scope") or []
        files: list[str] = []
        if isinstance(work_scope, list):
            files = [str(f) for f in work_scope if isinstance(f, str)]
        elif isinstance(work_scope, dict):
            raw_files = work_scope.get("files") or work_scope.get("files_modified") or []
            if isinstance(raw_files, list):
                files = [str(f) for f in raw_files]

        if files:
            db.chain_signals.emit_signal(
                chain_id,
                node_id,
                "file_claim",
                {"files": files[:50], "source": "baton_refresh"},
            )
    except Exception:
        logger.debug("File claim refresh failed for node %s", node_id, exc_info=True)
