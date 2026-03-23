"""Inter-wave judge agent and coherence review."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pixl.execution.chain.topology import detect_completed_wave

if TYPE_CHECKING:
    from pixl.storage.db.chain_plans import ChainPlanDB
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)


def check_and_run_judge(
    *,
    db: PixlDB,
    store: ChainPlanDB,
    chain_id: str,
    nodes: list[dict[str, Any]],
) -> str:
    """Run the judge agent between waves.  Returns 'pass', 'warn', or 'block'.

    Idempotent: checks for existing judge_finding signals to avoid re-running.
    """
    completed_wave = detect_completed_wave(nodes)
    if completed_wave is None:
        return "pass"

    # Idempotency: check if we already judged this wave
    existing = db.chain_signals.get_signals(
        chain_id,
        signal_type="judge_finding",
        limit=100,
    )
    for sig in existing:
        payload = sig.get("payload") or {}
        if payload.get("wave") == completed_wave:
            return str(payload.get("verdict", "pass"))

    wave_nodes = [n for n in nodes if int(n.get("wave", 0) or 0) == completed_wave]
    wave_summaries: list[str] = []
    for node in wave_nodes:
        node_id = str(node.get("node_id", ""))
        feature_id = str(node.get("feature_id", ""))
        feature = db.backlog.get_feature(feature_id) if feature_id else None
        title = str((feature or {}).get("title", node_id))
        status = str(node.get("status", ""))
        wave_summaries.append(f"- {title} ({node_id}): {status}")

    try:
        verdict = "pass"
        findings: list[dict[str, Any]] = []

        # Check for file overlaps across completed wave nodes
        file_claims = db.chain_signals.get_file_claims(chain_id)
        conflicting_files: list[str] = []
        for file_path, claimants in file_claims.items():
            wave_claimants = [
                c
                for c in claimants
                if any(
                    n.get("node_id") == c and int(n.get("wave", -1) or -1) == completed_wave
                    for n in nodes
                )
            ]
            if len(wave_claimants) > 1:
                conflicting_files.append(file_path)
                findings.append(
                    {
                        "category": "file_conflict",
                        "severity": "warn",
                        "description": f"File '{file_path}' modified by multiple nodes: {wave_claimants}",
                        "affected_nodes": wave_claimants,
                    }
                )

        # Check for blocker signals
        blockers = db.chain_signals.get_signals(
            chain_id,
            signal_type="blocker",
            limit=10,
        )
        for blocker in blockers:
            payload = blocker.get("payload") or {}
            findings.append(
                {
                    "category": "blocker",
                    "severity": "block",
                    "description": str(payload.get("description", "Blocker signal raised")),
                    "affected_nodes": [blocker.get("from_node", "")],
                }
            )
            verdict = "block"

        # Escalate to warn if conflicts found but no blockers
        if conflicting_files and verdict == "pass":
            verdict = "warn"

        db.chain_signals.emit_signal(
            chain_id,
            "judge",
            "judge_finding",
            {
                "wave": completed_wave,
                "verdict": verdict,
                "findings": findings[:10],
            },
        )

        return verdict
    except Exception:
        logger.debug(
            "Judge review failed for chain %s wave %d", chain_id, completed_wave, exc_info=True
        )
        # On failure, don't block the chain — emit a pass
        try:
            db.chain_signals.emit_signal(
                chain_id,
                "judge",
                "judge_finding",
                {"wave": completed_wave, "verdict": "pass", "error": "judge_unavailable"},
            )
        except Exception:
            logger.debug("Non-critical: judge fallback signal emission failed", exc_info=True)
        return "pass"
