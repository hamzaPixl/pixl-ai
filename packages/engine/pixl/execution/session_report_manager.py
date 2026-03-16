"""Session report manager for manual drafts and terminal auto-reporting."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pixl.utils.async_compat import run_coroutine_sync
from pixl.utils.versioning import suggest_next_version

logger = logging.getLogger(__name__)

_shared_sandbox_backend = None
_shared_backend_lock = threading.Lock()


def set_shared_sandbox_backend(backend: object) -> None:
    """Register the global DaytonaBackend so workflow runs reuse it."""
    global _shared_sandbox_backend
    with _shared_backend_lock:
        _shared_sandbox_backend = backend


def _get_shared_sandbox_backend():
    """Return the shared DaytonaBackend, or raise if none was registered."""
    with _shared_backend_lock:
        if _shared_sandbox_backend is None:
            raise RuntimeError("No shared DaytonaBackend registered")
        return _shared_sandbox_backend


REPORT_MODEL = "anthropic/claude-opus-4-6"
REPORT_PATH = "reports/session-audit.md"
REPORT_TASK_ID = "session-reporter"
SESSION_REPORT_MODEL_CONFIG_KEY = "session_report:model"
AUTO_TERMINAL_MAX_RETRIES = 3
AUTO_TERMINAL_RETRY_COOLDOWN_SECONDS = 300


class _NoAllowedReportModelError(RuntimeError):
    """Raised when providers config is loaded but no report model is allowlisted."""


def reports_enabled() -> bool:
    """Check if session report processing is enabled."""
    raw = os.environ.get("PIXL_SESSION_REPORT_DAEMON_ENABLED")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return True


def _auto_terminal_max_retries() -> int:
    """Maximum number of daemon retries after auto job failures."""
    raw = os.environ.get("PIXL_SESSION_REPORT_AUTO_MAX_RETRIES")
    if raw is None:
        return AUTO_TERMINAL_MAX_RETRIES
    try:
        return max(int(raw), 0)
    except ValueError:
        return AUTO_TERMINAL_MAX_RETRIES


def _auto_terminal_retry_cooldown_seconds() -> int:
    """Minimum wait time before retrying a failed auto job."""
    raw = os.environ.get("PIXL_SESSION_REPORT_AUTO_RETRY_COOLDOWN_SECONDS")
    if raw is None:
        return AUTO_TERMINAL_RETRY_COOLDOWN_SECONDS
    try:
        return max(int(raw), 0)
    except ValueError:
        return AUTO_TERMINAL_RETRY_COOLDOWN_SECONDS


def _parse_iso_timestamp(raw: Any) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _failed_auto_job_retry_allowed(
    job: dict[str, Any], *, max_retries: int, cooldown_seconds: int
) -> bool:
    """Return True when a failed auto-terminal job should be requeued."""
    try:
        retry_count = int(job.get("retry_count") or 0)
    except (TypeError, ValueError):
        retry_count = 0
    if retry_count >= max_retries:
        return False

    last_failed_at = (
        _parse_iso_timestamp(job.get("completed_at"))
        or _parse_iso_timestamp(job.get("updated_at"))
        or _parse_iso_timestamp(job.get("created_at"))
    )
    if last_failed_at is None:
        return True

    if last_failed_at.tzinfo is None:
        now = datetime.now()
    else:
        now = datetime.now(tz=last_failed_at.tzinfo)
    elapsed_seconds = max((now - last_failed_at).total_seconds(), 0.0)
    return elapsed_seconds >= float(cooldown_seconds)


def _build_report_prompt(
    *,
    audit_payload: dict[str, Any],
    session_id: str,
    trigger: str,
    terminal_status: str | None,
) -> str:
    """Build markdown-generation prompt from structured audit data."""
    trigger_line = f"trigger={trigger}"
    if terminal_status:
        trigger_line += f", terminal_status={terminal_status}"

    return (
        "You are an expert workflow reliability reviewer.\n"
        "Generate an insightful, evidence-based markdown session report.\n\n"
        "Requirements:\n"
        "- Be concise and specific. Avoid generic advice.\n"
        "- Ground claims in the provided metrics/events/issues.\n"
        "- Prioritize the most impactful actions first.\n"
        "- If uncertainty exists, state it explicitly.\n\n"
        "Output format (markdown):\n"
        "# Session Report: <session_id>\n"
        "## Session Snapshot\n"
        "## Executive Assessment\n"
        "## What Went Well\n"
        "## What Went Wrong\n"
        "## Timeline Highlights\n"
        "## Cost & Efficiency Signals\n"
        "## Prioritized Recommendations\n"
        "## Next-Run Checklist\n\n"
        f"Context:\n{trigger_line}\n"
        f"session_id={session_id}\n\n"
        "Structured audit JSON:\n"
        "```json\n"
        f"{json.dumps(audit_payload, indent=2, default=str)}\n"
        "```\n"
    )


def _resolve_project_root(project_path: Path) -> Path:
    """Resolve actual repo root for model context when available."""
    from pixl.projects.registry import get_project

    info = get_project(project_path.name)
    if info and info.get("project_root"):
        return Path(str(info["project_root"]))
    return project_path


def resolve_report_model(project_root: Path, *, db_override_model: str | None = None) -> str:
    """Resolve LLM model for reporting with env/config fallback."""
    try:
        from pixl.config.providers import load_providers_config

        cfg = load_providers_config(project_root)
        default_model = str(getattr(cfg, "default_model", "") or "").strip()

        def _normalize(candidate: str) -> str:
            if not candidate:
                return ""
            provider, model_name = cfg.parse_model_string(candidate)
            if "/" in candidate:
                return candidate
            return f"{provider}/{model_name}"

        env_model_raw = (os.environ.get("PIXL_SESSION_REPORT_MODEL") or "").strip()
        if env_model_raw:
            env_model = _normalize(env_model_raw)
            if cfg.is_allowed_model(env_model):
                return env_model
            logger.warning(
                "PIXL_SESSION_REPORT_MODEL=%s not in allowlist; falling back to providers default",
                env_model_raw,
            )

        db_model_raw = str(db_override_model or "").strip()
        if db_model_raw:
            db_model = _normalize(db_model_raw)
            if cfg.is_allowed_model(db_model):
                return db_model
            logger.warning(
                "session_report:model=%s not in allowlist; falling back to providers default",
                db_model_raw,
            )

        configured = _normalize(default_model)
        if configured and cfg.is_allowed_model(configured):
            return configured

        fallback = _normalize(REPORT_MODEL)
        if fallback and cfg.is_allowed_model(fallback):
            return fallback

        configured_models = getattr(cfg, "models", None)
        if isinstance(configured_models, list):
            for candidate in configured_models:
                normalized = _normalize(str(candidate or "").strip())
                if normalized and cfg.is_allowed_model(normalized):
                    return normalized
        raise _NoAllowedReportModelError(
            "No allowed report model configured. Set PIXL_SESSION_REPORT_MODEL "
            "or update providers.yaml allowlist/default_model."
        )
    except _NoAllowedReportModelError:
        raise
    except Exception:
        logger.debug("Unable to load providers config for session report model", exc_info=True)
    return REPORT_MODEL


def _next_report_version(existing_versions: list[dict[str, Any]]) -> tuple[str, str | None]:
    """Return semantic version and previous version id for report artifact."""
    if not existing_versions:
        return "1.0.0", None

    previous = existing_versions[-1]
    previous_id = str(previous.get("id") or "")
    seen_versions = [str(v.get("version")) for v in existing_versions if v.get("version")]
    if not seen_versions:
        return "1.0.1", (previous_id or None)
    return suggest_next_version(seen_versions, "patch"), (previous_id or None)


def generate_session_report(
    *,
    db: Any,
    project_path: Path,
    session_id: str,
    trigger: str,
    terminal_status: str | None,
    job_id: str,
) -> str:
    """Generate markdown report via LLM and persist it as session artifact.

    Returns:
        artifact_id
    """
    # Build audit payload directly from DB (SessionAuditor was removed with diagnostics/)
    session = db.sessions.get_session(session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    events = db.events.get_session_events(session_id)
    payload = {
        "session_id": session_id,
        "status": session.get("status", "unknown"),
        "events_count": len(events),
        "events": events[:50],  # cap for prompt size
    }
    prompt = _build_report_prompt(
        audit_payload=payload,
        session_id=session_id,
        trigger=trigger,
        terminal_status=terminal_status,
    )

    from pixl.orchestration.core import OrchestratorCore
    from pixl.orchestration.resolve import resolve_execution_backend

    project_root = _resolve_project_root(project_path)
    model_override = None
    try:
        model_override = db.get_config(SESSION_REPORT_MODEL_CONFIG_KEY)
    except Exception:
        logger.debug("Unable to read session report model override", exc_info=True)
    model_name = resolve_report_model(project_root, db_override_model=model_override)

    sandbox_backend = None
    backend = resolve_execution_backend(project_root)
    if backend == "sandbox":
        try:
            sandbox_backend = _get_shared_sandbox_backend()
        except RuntimeError:
            if os.environ.get("PIXL_REQUIRE_SANDBOX", "").strip().lower() in ("1", "true", "yes"):
                raise RuntimeError("PIXL_REQUIRE_SANDBOX is set but no sandbox backend registered for reports")
            logger.warning("Shared DaytonaBackend not registered — report will use SDK backend")
    orchestrator = OrchestratorCore(project_root, sandbox_backend=sandbox_backend)
    llm_text, metadata = run_coroutine_sync(
        orchestrator.query_with_streaming(
            prompt=prompt,
            model=model_name,
            max_turns=4,
            feature_id=session.get("feature_id"),
            stream_callback=lambda _m: None,
            stage_id="session-report",
            agent_name="reviewer",
        )
    )
    if not metadata.get("success"):
        error = str(metadata.get("error") or "unknown llm error")
        raise RuntimeError(f"LLM report generation failed: {error}")
    markdown = str(llm_text or "").strip()
    if not markdown:
        raise RuntimeError("LLM report generation returned empty output")

    existing = db.artifacts.list_versions_by_path(REPORT_PATH, session_id)
    version, previous_version_id = _next_report_version(existing)
    artifact = db.artifacts.put(
        session_id=session_id,
        logical_path=REPORT_PATH,
        content=markdown,
        artifact_type="review",
        task_id=REPORT_TASK_ID,
        name="session-audit.md",
        feature_id=session.get("feature_id") if (session.get("feature_id") or "").startswith("feat-") else None,
        tags=["session-report", "audit", "llm"],
        extra={
            "report_kind": "terminal" if trigger == "auto_terminal" else "draft",
            "trigger": trigger,
            "terminal_status": terminal_status,
            "job_id": job_id,
            "session_status_snapshot": session.get("status", "unknown"),
            "model_used": model_name,
        },
        version=version,
        previous_version_id=previous_version_id,
        change_description=f"Session report generated ({trigger})",
        mime_type="text/markdown",
    )
    artifact_id = str(artifact.get("id") or "")
    if not artifact_id:
        raise RuntimeError("Failed to persist report artifact")
    return artifact_id


class SessionReportManager:
    """Static helper methods for session report job processing.

    No longer manages daemon threads — the UnifiedScheduler drives
    report processing via its async loop.
    """

    @staticmethod
    def _enqueue_missing_auto_jobs(db: Any) -> None:
        """Ensure one auto report job exists for the latest terminal session outcome."""
        conn = db.conn
        existing_rows = conn.execute(
            """SELECT idempotency_key
                     , id
                     , status
                     , retry_count
                     , created_at
                     , updated_at
                     , completed_at
               FROM session_report_jobs
               WHERE trigger = 'auto_terminal'
                 AND idempotency_key IS NOT NULL"""
        ).fetchall()
        existing_by_key = {
            str(r["idempotency_key"]): dict(r) for r in existing_rows if r["idempotency_key"]
        }
        max_retries = _auto_terminal_max_retries()
        cooldown_seconds = _auto_terminal_retry_cooldown_seconds()

        rows = conn.execute(
            """
            SELECT ws.id AS session_id,
                   term.event_type AS terminal_event
            FROM workflow_sessions ws
            JOIN (
                SELECT ranked.session_id, ranked.event_type
                FROM (
                    SELECT e.session_id,
                           e.event_type,
                           ROW_NUMBER() OVER (
                               PARTITION BY e.session_id
                               ORDER BY datetime(REPLACE(e.created_at, 'T', ' ')) DESC, e.id DESC
                           ) AS rn
                    FROM events e
                    WHERE e.event_type IN ('session_completed', 'session_failed')
                ) ranked
                WHERE ranked.rn = 1
            ) term
              ON term.session_id = ws.id
            WHERE ws.ended_at IS NOT NULL
            """
        ).fetchall()

        for row in rows:
            session_id = str(row["session_id"])
            terminal_event = str(row["terminal_event"] or "")
            if terminal_event == "session_completed":
                terminal_status = "completed"
            elif terminal_event == "session_failed":
                terminal_status = "failed"
            else:
                continue

            key = f"auto_terminal:{session_id}:{terminal_status}"
            existing = existing_by_key.get(key)
            if existing is not None:
                status = str(existing.get("status") or "")
                if status in {"queued", "running", "completed"}:
                    continue
                if status != "failed":
                    continue
                if max_retries <= 0:
                    continue
                if not _failed_auto_job_retry_allowed(
                    existing,
                    max_retries=max_retries,
                    cooldown_seconds=cooldown_seconds,
                ):
                    continue
                if db.sessions.requeue_session_report_job(str(existing["id"])):
                    existing["status"] = "queued"
                    existing_by_key[key] = existing
                continue
            db.sessions.enqueue_session_report_job(
                session_id=session_id,
                trigger="auto_terminal",
                terminal_status=terminal_status,
                requested_by="daemon",
                idempotency_key=key,
            )
            existing_by_key[key] = {"status": "queued"}

    @staticmethod
    def _drain_queue(db: Any, project_path: Path) -> None:
        """Process queued jobs until queue is empty."""
        while True:
            job = db.sessions.claim_next_session_report_job()
            if job is None:
                return

            job_id = str(job["id"])
            session_id = str(job["session_id"])
            trigger = str(job.get("trigger") or "manual_draft")
            terminal_status = (
                str(job.get("terminal_status"))
                if job.get("terminal_status") is not None
                else None
            )
            try:
                artifact_id = generate_session_report(
                    db=db,
                    project_path=project_path,
                    session_id=session_id,
                    trigger=trigger,
                    terminal_status=terminal_status,
                    job_id=job_id,
                )
                with db.events.batch():
                    completed = db.sessions.complete_session_report_job(job_id, artifact_id)
                    if not completed:
                        raise RuntimeError(f"Unable to mark job {job_id} completed")
                    db.events.emit(
                        event_type="session_report_generated",
                        session_id=session_id,
                        payload={
                            "job_id": job_id,
                            "artifact_id": artifact_id,
                            "trigger": trigger,
                            "terminal_status": terminal_status,
                        },
                    )
            except Exception as exc:
                try:
                    with db.events.batch():
                        marked_failed = db.sessions.fail_session_report_job(job_id, str(exc))
                        db.events.emit(
                            event_type="session_report_failed",
                            session_id=session_id,
                            payload={
                                "job_id": job_id,
                                "trigger": trigger,
                                "terminal_status": terminal_status,
                                "error": str(exc),
                            },
                        )
                except Exception:
                    logger.error(
                        "Failed to emit session_report_failed for job %s",
                        job_id,
                        exc_info=True,
                    )
                    marked_failed = False
                if not marked_failed:
                    logger.warning("Session report job %s could not be marked failed", job_id)
                logger.warning("Session report job %s failed: %s", job_id, exc)
            finally:
                # Keep loop cooperative under sustained queue pressure.
                time.sleep(0.01)
