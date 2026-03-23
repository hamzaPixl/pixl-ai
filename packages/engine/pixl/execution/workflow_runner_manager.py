"""In-process workflow runner supervisor for stalled session recovery."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.storage.db.connection import PixlDB

if TYPE_CHECKING:
    from pixl.orchestration.core import OrchestratorCore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RunnerKey:
    db_path: str
    session_id: str


class WorkflowRunnerManager:
    """In-process workflow runner supervisor (one thread per running session)."""

    _lock = threading.RLock()
    _threads: dict[_RunnerKey, threading.Thread] = {}
    _stop_events: dict[_RunnerKey, threading.Event] = {}
    _orchestrators: dict[str, OrchestratorCore] = {}  # session_id -> orchestrator
    _reconciled_db_paths: set[str] = set()

    @classmethod
    def reconcile(cls, *, db: PixlDB, project_path: Path) -> None:
        """Start runners for stalled sessions after API restart."""
        db_path = str(getattr(db, "db_path", ""))
        with cls._lock:
            if db_path in cls._reconciled_db_paths:
                return
            cls._reconciled_db_paths.add(db_path)

        stalled_session_ids = db.sessions.list_stalled_running_sessions()
        for session_id in stalled_session_ids:
            try:
                cls.start_session(
                    db=db,
                    project_path=project_path,
                    session_id=session_id,
                    workflow_id="recovered",
                    skip_approval=False,
                )
            except Exception:
                logger.exception("Failed to reconcile workflow session %s", session_id)

    @classmethod
    def start_session(
        cls,
        *,
        db: PixlDB,
        project_path: Path,
        session_id: str,
        workflow_id: str,
        skip_approval: bool,
        reclaim_payload: dict[str, Any] | None = None,
    ) -> bool:
        """Ensure a runner thread is active for *session_id* (idempotent)."""
        key = _RunnerKey(db_path=str(getattr(db, "db_path", "")), session_id=session_id)

        with cls._lock:
            existing = cls._threads.get(key)
            if existing and existing.is_alive():
                return False

            if reclaim_payload:
                try:
                    db.events.emit(
                        event_type="session_reclaimed",
                        session_id=session_id,
                        payload=reclaim_payload,
                    )
                except Exception:
                    logger.exception("Failed to emit session_reclaimed for %s", session_id)

            stop_event = threading.Event()
            cls._stop_events[key] = stop_event

            def _runner() -> None:
                try:
                    from pixl.execution.workflow_runner import run_workflow as _run_workflow

                    _run_workflow(
                        project_path=project_path,
                        session_id=session_id,
                        workflow_id=workflow_id,
                        skip_approval=skip_approval,
                        db=db,
                        stop_event=stop_event,
                    )
                except Exception:
                    logger.exception("Workflow runner thread crashed for session %s", session_id)
                finally:
                    with cls._lock:
                        current = cls._threads.get(key)
                        if current is threading.current_thread():
                            cls._threads.pop(key, None)
                        cls._stop_events.pop(key, None)
                        cls._orchestrators.pop(session_id, None)

            thread = threading.Thread(
                target=_runner,
                daemon=True,
                name=f"pixl-workflow-runner:{session_id}",
            )
            cls._threads[key] = thread
            thread.start()

            return True

    @classmethod
    def register_orchestrator(cls, session_id: str, orchestrator: OrchestratorCore) -> None:
        """Register an orchestrator for a running session (enables interrupt)."""
        with cls._lock:
            cls._orchestrators[session_id] = orchestrator

    @classmethod
    def unregister_orchestrator(cls, session_id: str) -> None:
        """Unregister an orchestrator when a session ends."""
        with cls._lock:
            cls._orchestrators.pop(session_id, None)

    @classmethod
    def get_stop_event(cls, session_id: str) -> threading.Event | None:
        """Return the stop event for a session (used by recovery backoff)."""
        with cls._lock:
            for key, event in cls._stop_events.items():
                if key.session_id == session_id:
                    return event
        return None

    @classmethod
    def interrupt_session(cls, session_id: str) -> bool:
        """Interrupt a running session's active SDK query.

        Returns True if an orchestrator was found and interrupted.
        """
        with cls._lock:
            orchestrator = cls._orchestrators.get(session_id)

        if orchestrator is not None:
            orchestrator.request_interrupt()
            logger.info("Interrupt signal sent to session %s", session_id)
            return True

        logger.debug(
            "No orchestrator found for session %s (may not be in an active query)", session_id
        )
        return False

    @classmethod
    def stop_session(cls, key: _RunnerKey) -> None:
        """Signal a runner thread to stop and wait for it."""
        with cls._lock:
            stop_event = cls._stop_events.get(key)
            thread = cls._threads.get(key)

        if stop_event:
            stop_event.set()
        if thread and thread.is_alive():
            thread.join(timeout=5.0)

    @classmethod
    def stop_all(cls, timeout: float = 5.0) -> None:
        """Stop all active runner threads."""
        with cls._lock:
            keys = list(cls._stop_events.keys())
            for stop_event in cls._stop_events.values():
                stop_event.set()
            threads = [(k, cls._threads.get(k)) for k in keys]

        for _key, thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=timeout)

    @classmethod
    def running_count(cls) -> int:
        """Return the number of currently alive runner threads."""
        with cls._lock:
            return sum(1 for t in cls._threads.values() if t.is_alive())
