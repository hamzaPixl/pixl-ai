"""Autonomy subsystem for gate auto-approval decisions.

Implements a confidence-scored autonomy ladder with promotion/demotion
for deciding when to auto-approve workflow gates.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Supervised mode defaults:
# Autopilot can auto-approve gates only when historical confidence is high.
SUPERVISED_MIN_SAMPLES = 3
SUPERVISED_CONFIDENCE_THRESHOLD = 0.90
AUTOPILOT_CONFIDENCE_THRESHOLD = 0.70
PROMOTE_LEVEL_2_THRESHOLD = 0.95
DEMOTE_THRESHOLD = 0.70


def _autonomy_key(feature_id: str) -> str:
    """Config key for feature-level autonomy mode."""
    return f"autonomy:{feature_id}"


def _parse_float_config(raw: str | None, default: float) -> float:
    """Parse float config with fallback and clamping to [0, 1]."""
    if raw is None:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, value))


def _parse_int_config(raw: str | None, default: int) -> int:
    """Parse integer config with fallback."""
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def _failure_signals() -> set[str]:
    return {
        "session_failed",
        "task_failed",
        "gate_rejected",
        "contract_violation",
        "recovery_escalated",
    }


def _estimate_feature_confidence(
    db: Any,
    feature_id: str,
    *,
    exclude_session_id: str | None = None,
    lookback_sessions: int = 20,
) -> tuple[float, int]:
    """Estimate feature confidence from recent completed sessions.

    A "successful" session is one that:
    - emitted session_completed
    - did not emit failure/rejection/escalation signals
    """
    conn = getattr(db, "conn", None)
    if conn is None:
        return 0.0, 0

    query = """
        SELECT id
        FROM workflow_sessions
        WHERE feature_id = ?
          AND ended_at IS NOT NULL
    """
    params: list[Any] = [feature_id]

    if exclude_session_id:
        query += " AND id != ?"
        params.append(exclude_session_id)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(lookback_sessions)

    rows = conn.execute(query, tuple(params)).fetchall()
    session_ids = [r["id"] for r in rows]
    if not session_ids:
        return 0.0, 0

    failure_sigs = _failure_signals()
    success_count = 0
    for sid in session_ids:
        events = db.events.get_events(session_id=sid)
        event_types = {e.get("event_type", "") for e in events}
        if "session_completed" in event_types and not (event_types & failure_sigs):
            success_count += 1

    total = len(session_ids)
    confidence = success_count / total if total > 0 else 0.0
    return confidence, total


def _estimate_agent_task_confidence(
    db: Any,
    feature_id: str,
    *,
    agent_name: str,
    task_key: str,
    exclude_session_id: str | None = None,
    lookback_sessions: int = 20,
) -> tuple[float, int]:
    """Estimate confidence for a specific agent/task pair on a feature."""
    conn = getattr(db, "conn", None)
    if conn is None:
        return 0.0, 0

    query = """
        SELECT id
        FROM workflow_sessions
        WHERE feature_id = ?
          AND ended_at IS NOT NULL
    """
    params: list[Any] = [feature_id]

    if exclude_session_id:
        query += " AND id != ?"
        params.append(exclude_session_id)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(lookback_sessions)

    rows = conn.execute(query, tuple(params)).fetchall()
    session_ids = [r["id"] for r in rows]
    if not session_ids:
        return 0.0, 0

    failure_sigs = _failure_signals()
    success_count = 0
    samples = 0

    for sid in session_ids:
        node_row = conn.execute(
            """
            SELECT state
            FROM node_instances
            WHERE session_id = ?
              AND agent_name = ?
              AND node_id = ?
            LIMIT 1
            """,
            (sid, agent_name, task_key),
        ).fetchone()
        if not node_row:
            continue

        samples += 1
        events = db.events.get_events(session_id=sid)
        event_types = {e.get("event_type", "") for e in events}
        if (
            node_row["state"] == "task_completed"
            and "session_completed" in event_types
            and not (event_types & failure_sigs)
        ):
            success_count += 1

    confidence = success_count / samples if samples > 0 else 0.0
    return confidence, samples


def resolve_latest_agent_task_pair(session: Any) -> tuple[str, str]:
    """Resolve the most recent task's (agent_name, node_id) pair."""
    candidates: list[tuple[str, str, str]] = []
    for node_id, instance in session.node_instances.items():
        state = instance.get("state")
        if state not in {"task_completed", "task_running", "task_failed"}:
            continue

        agent_name = instance.get("agent_name")
        if not agent_name:
            continue

        timestamp = (
            instance.get("ended_at") or instance.get("started_at") or instance.get("ready_at") or ""
        )
        candidates.append((timestamp, agent_name, node_id))

    if not candidates:
        return "unknown", "workflow"

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, agent_name, node_id = candidates[0]
    return agent_name, node_id


def _load_autonomy_profile(
    db: Any,
    *,
    feature_id: str,
    agent_name: str,
    task_key: str,
) -> dict[str, Any] | None:
    """Load persisted autonomy profile for a feature agent/task pair."""
    conn = getattr(db, "conn", None)
    if conn is None:
        return None

    try:
        row = conn.execute(
            """
            SELECT feature_id, agent_name, task_key, mode, level, confidence, samples, last_reason
            FROM autonomy_profiles
            WHERE feature_id = ?
              AND agent_name = ?
              AND task_key = ?
            """,
            (feature_id, agent_name, task_key),
        ).fetchone()
    except Exception:
        return None

    return dict(row) if row else None


def _upsert_autonomy_profile(
    db: Any,
    *,
    feature_id: str,
    agent_name: str,
    task_key: str,
    mode: str,
    level: int,
    confidence: float,
    samples: int,
    reason: str,
) -> None:
    """Persist autonomy profile updates."""
    conn = getattr(db, "conn", None)
    if conn is None:
        return

    try:
        conn.execute(
            """
            INSERT INTO autonomy_profiles
                (feature_id, agent_name, task_key, mode, level, confidence, samples, last_reason, updated_at)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(feature_id, agent_name, task_key) DO UPDATE SET
                mode = excluded.mode,
                level = excluded.level,
                confidence = excluded.confidence,
                samples = excluded.samples,
                last_reason = excluded.last_reason,
                updated_at = datetime('now')
            """,
            (
                feature_id,
                agent_name,
                task_key,
                mode,
                level,
                confidence,
                samples,
                reason,
            ),
        )
        conn.commit()
    except Exception:
        # Profile persistence is best-effort; gate execution should not fail.
        logger.warning(
            "Failed to upsert autonomy profile for feature=%s agent=%s task=%s",
            feature_id,
            agent_name,
            task_key,
            exc_info=True,
        )


def _reconcile_autonomy_level(
    *,
    previous_level: int,
    confidence: float,
    samples: int,
    min_samples: int,
) -> tuple[int, str]:
    """Compute next autonomy level from confidence and history depth."""
    if samples < min_samples:
        # Keep level 0 until enough history is available.
        return 0, "insufficient_history"

    level = previous_level
    reason = "stable"

    if confidence >= PROMOTE_LEVEL_2_THRESHOLD:
        if level < 2:
            level += 1
            reason = "promoted"
    elif confidence >= SUPERVISED_CONFIDENCE_THRESHOLD:
        if level < 1:
            level = 1
            reason = "promoted"
    elif confidence < DEMOTE_THRESHOLD:
        if level > 0:
            level -= 1
            reason = "demoted"
        else:
            reason = "below_threshold"

    return level, reason


def should_auto_approve_waiting_gate(
    db: Any,
    *,
    session_id: str,
    feature_id: str | None,
    skip_approval: bool,
    agent_name: str = "unknown",
    task_key: str = "workflow",
) -> dict[str, Any]:
    """Decide whether a waiting gate should be auto-approved.

    Phase 2 policy:
    - --yes / skip_approval always auto-approves
    - assist never auto-approves
    - autopilot uses a confidence-scored autonomy ladder with promotion/demotion
    """
    if skip_approval:
        return {
            "approve": True,
            "mode": "override",
            "reason": "skip_approval",
            "confidence": 1.0,
            "threshold": 0.0,
            "samples": 0,
            "min_samples": 0,
            "level": 3,
            "previous_level": 3,
            "confidence_source": "override",
            "agent_name": agent_name,
            "task_key": task_key,
        }

    if not feature_id:
        return {
            "approve": False,
            "mode": "assist",
            "reason": "missing_feature_id",
            "confidence": 0.0,
            "threshold": 1.0,
            "samples": 0,
            "min_samples": SUPERVISED_MIN_SAMPLES,
            "level": 0,
            "previous_level": 0,
            "confidence_source": "none",
            "agent_name": agent_name,
            "task_key": task_key,
        }

    raw_mode = db.get_config(_autonomy_key(feature_id), default="assist")
    mode = raw_mode if raw_mode in ("assist", "autopilot") else "assist"

    supervised_threshold = _parse_float_config(
        db.get_config(
            "autonomy:supervised_threshold", default=str(SUPERVISED_CONFIDENCE_THRESHOLD)
        ),
        SUPERVISED_CONFIDENCE_THRESHOLD,
    )
    autopilot_threshold = _parse_float_config(
        db.get_config("autonomy:autopilot_threshold", default=str(AUTOPILOT_CONFIDENCE_THRESHOLD)),
        AUTOPILOT_CONFIDENCE_THRESHOLD,
    )
    min_samples = _parse_int_config(
        db.get_config("autonomy:supervised_min_samples", default=str(SUPERVISED_MIN_SAMPLES)),
        SUPERVISED_MIN_SAMPLES,
    )

    pair_confidence, pair_samples = _estimate_agent_task_confidence(
        db,
        feature_id,
        agent_name=agent_name,
        task_key=task_key,
        exclude_session_id=session_id,
    )
    feature_confidence, feature_samples = _estimate_feature_confidence(
        db,
        feature_id,
        exclude_session_id=session_id,
    )

    if pair_samples > 0:
        confidence = pair_confidence
        samples = pair_samples
        confidence_source = "agent_task"
    else:
        confidence = feature_confidence
        samples = feature_samples
        confidence_source = "feature"

    profile = _load_autonomy_profile(
        db,
        feature_id=feature_id,
        agent_name=agent_name,
        task_key=task_key,
    )
    previous_level = int(profile["level"]) if profile else 0

    level, level_reason = _reconcile_autonomy_level(
        previous_level=previous_level,
        confidence=confidence,
        samples=samples,
        min_samples=min_samples,
    )

    if mode != "autopilot":
        level = 0
        threshold = supervised_threshold
        reason = "assist_mode"
        approve = False
    else:
        if level >= 2:
            threshold = autopilot_threshold
        else:
            threshold = supervised_threshold

        if samples < min_samples:
            reason = "insufficient_history"
            approve = False
        elif level < 1:
            reason = "trust_level_too_low"
            approve = False
        else:
            approve = confidence >= threshold
            reason = "confidence_threshold_met" if approve else "below_threshold"

    if mode == "autopilot":
        persist_reason = (
            reason if reason != "confidence_threshold_met" else f"{level_reason}:{reason}"
        )
    else:
        persist_reason = reason

    _upsert_autonomy_profile(
        db,
        feature_id=feature_id,
        agent_name=agent_name,
        task_key=task_key,
        mode=mode,
        level=level,
        confidence=confidence,
        samples=samples,
        reason=persist_reason,
    )

    return {
        "approve": approve,
        "mode": mode,
        "reason": reason,
        "confidence": round(confidence, 4),
        "threshold": threshold,
        "samples": samples,
        "min_samples": min_samples,
        "level": level,
        "previous_level": previous_level,
        "confidence_source": confidence_source,
        "agent_name": agent_name,
        "task_key": task_key,
    }


def should_auto_merge_pr(
    db: Any,
    *,
    session_id: str,
    feature_id: str | None,
    skip_approval: bool,
) -> dict[str, Any]:
    """Decision helper for PR auto-merge under the autonomy ladder.

    This uses the same supervised/autopilot thresholds as gate auto-approval,
    but writes its own autonomy profile key via (agent_name="gh", task_key="pr_merge")
    so merge decisions are tracked separately.
    """
    return should_auto_approve_waiting_gate(
        db,
        session_id=session_id,
        feature_id=feature_id,
        skip_approval=skip_approval,
        agent_name="gh",
        task_key="pr_merge",
    )


def record_autonomy_outcome(db: Any, session: Any) -> None:
    """Persist autonomy outcome metrics for a terminal session."""
    if not session or not session.feature_id:
        return

    conn = getattr(db, "conn", None)
    if conn is None:
        return

    events = db.events.get_events(session_id=session.id)
    auto_approved_gates = 0
    manual_gate_approvals = 0
    gate_rejections = 0
    recovery_cycles = 0
    recovery_escalations = 0

    for event in events:
        event_type = event.get("event_type")
        payload = event.get("payload") or {}

        if event_type == "gate_approved":
            if payload.get("approver") == "auto":
                auto_approved_gates += 1
            else:
                manual_gate_approvals += 1
        elif event_type == "gate_rejected":
            gate_rejections += 1
        elif event_type == "recovery_requested":
            recovery_cycles += 1
        elif event_type == "recovery_escalated":
            recovery_escalations += 1

    human_interventions = manual_gate_approvals + gate_rejections + recovery_escalations
    agent_name, task_key = resolve_latest_agent_task_pair(session)
    mode_raw = db.get_config(_autonomy_key(session.feature_id), default="assist")
    mode = mode_raw if mode_raw in ("assist", "autopilot") else "assist"

    profile = _load_autonomy_profile(
        db,
        feature_id=session.feature_id,
        agent_name=agent_name,
        task_key=task_key,
    )
    level = int(profile["level"]) if profile else 0
    confidence = float(profile["confidence"]) if profile else 0.0
    samples = int(profile["samples"]) if profile else 0

    try:
        conn.execute(
            """
            INSERT INTO autonomy_outcomes
                (session_id, feature_id, agent_name, task_key, mode, level, confidence, samples,
                 auto_approved_gates, manual_gate_approvals, gate_rejections, recovery_cycles, human_interventions)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                feature_id = excluded.feature_id,
                agent_name = excluded.agent_name,
                task_key = excluded.task_key,
                mode = excluded.mode,
                level = excluded.level,
                confidence = excluded.confidence,
                samples = excluded.samples,
                auto_approved_gates = excluded.auto_approved_gates,
                manual_gate_approvals = excluded.manual_gate_approvals,
                gate_rejections = excluded.gate_rejections,
                recovery_cycles = excluded.recovery_cycles,
                human_interventions = excluded.human_interventions
            """,
            (
                session.id,
                session.feature_id,
                agent_name,
                task_key,
                mode,
                level,
                confidence,
                samples,
                auto_approved_gates,
                manual_gate_approvals,
                gate_rejections,
                recovery_cycles,
                human_interventions,
            ),
        )
        conn.commit()
    except Exception:
        logger.warning(
            "Failed to persist autonomy outcome for session %s", session.id, exc_info=True
        )
