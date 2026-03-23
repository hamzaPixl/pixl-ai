"""ChainRunnerManager: in-process chain runner supervisor."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pixl.execution.chain.config import load_chain_exec_config, save_chain_exec_config
from pixl.execution.chain.paths import resolve_project_root
from pixl.execution.git_utils import (
    git_rev_parse,
    git_symbolic_head,
    refresh_base_ref,
)

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RunnerKey:
    db_path: str
    chain_id: str


class ChainRunnerManager:
    """In-process chain runner supervisor (one thread per running chain)."""

    _lock = threading.RLock()
    _threads: dict[_RunnerKey, threading.Thread] = {}
    _stop_events: dict[_RunnerKey, threading.Event] = {}
    _reconciled_db_paths: set[str] = set()

    @classmethod
    def reconcile(cls, *, db: PixlDB) -> None:
        """Start runners for any chains persisted as 'running'/'paused' after restart."""
        db_path = str(getattr(db, "db_path", ""))
        with cls._lock:
            if db_path in cls._reconciled_db_paths:
                return
            cls._reconciled_db_paths.add(db_path)

        # Guard: skip reconciliation if the project root is not a git repo.
        # Standalone-mode tmp projects (e.g. from tests) may lack a .git dir,
        # causing every start_chain attempt to fail with git errors.
        project_root = resolve_project_root(db)
        if not (project_root / ".git").exists():
            logger.warning(
                "Skipping chain reconciliation — project root %s is not a git repository",
                project_root,
            )
            return

        rows = db.conn.execute(
            "SELECT id FROM execution_chains WHERE status IN ('running', 'paused') ORDER BY updated_at DESC",
        ).fetchall()
        for row in rows:
            chain_id = str(row["id"])
            cfg = load_chain_exec_config(db, chain_id)
            workflow_id = str(cfg.get("workflow_id") or "tdd")
            skip_approval = bool(cfg.get("skip_approval") or False)
            try:
                cls.start_chain(
                    db=db,
                    chain_id=chain_id,
                    workflow_id=workflow_id,
                    skip_approval=skip_approval,
                )
            except Exception:
                logger.exception("Failed to reconcile chain runner for %s", chain_id)

    @classmethod
    def start_chain(
        cls,
        *,
        db: PixlDB,
        chain_id: str,
        workflow_id: str,
        skip_approval: bool,
    ) -> None:
        """Ensure a runner is active for *chain_id* (idempotent)."""
        from pixl.execution.chain.runner import run_chain_loop

        key = _RunnerKey(db_path=str(getattr(db, "db_path", "")), chain_id=chain_id)

        with cls._lock:
            existing = cls._threads.get(key)
            if existing and existing.is_alive():
                return

            cfg = load_chain_exec_config(db, chain_id)
            base_remote = str(cfg.get("base_remote") or "origin")
            base_branch = str(cfg.get("base_branch") or "")
            project_root = resolve_project_root(db)
            if not base_branch:
                detected, err = git_symbolic_head(project_root)
                if err or not detected:
                    raise RuntimeError(f"git_base_branch_required:{err or 'detached_head'}")
                base_branch = detected

            base_ref = str(cfg.get("base_ref") or "")
            if not base_ref:
                # Default to the local HEAD commit (works for local-only repos and tests).
                head, err = git_rev_parse(project_root, "HEAD")
                if head and not err:
                    base_ref = head
                else:
                    refreshed, fetch_err = refresh_base_ref(
                        project_root,
                        remote=base_remote,
                        base_branch=base_branch,
                    )
                    base_ref = refreshed or ""
                    if not base_ref:
                        raise RuntimeError(
                            f"git_base_ref_unavailable:{fetch_err or err or 'unknown'}"
                        )

            save_chain_exec_config(
                db,
                chain_id,
                workflow_id=workflow_id,
                skip_approval=skip_approval,
                base_remote=base_remote,
                base_branch=base_branch,
                base_ref=base_ref,
                pr_automation_enabled=bool(cfg.get("pr_automation", True)),
                merge_method=str(cfg.get("merge_method") or "squash"),
            )

            stop_event = threading.Event()
            cls._stop_events[key] = stop_event

            thread = threading.Thread(
                target=run_chain_loop,
                kwargs={
                    "db": db,
                    "chain_id": chain_id,
                    "stop_event": stop_event,
                },
                daemon=True,
                name=f"pixl-chain-runner:{chain_id}",
            )
            cls._threads[key] = thread
            thread.start()

    @classmethod
    def stop_chain(cls, key: _RunnerKey) -> None:
        """Signal a chain runner thread to stop and wait for it."""
        with cls._lock:
            stop_event = cls._stop_events.get(key)
            thread = cls._threads.get(key)

        if stop_event:
            stop_event.set()
        if thread and thread.is_alive():
            thread.join(timeout=5.0)

    @classmethod
    def stop_all(cls, timeout: float = 5.0) -> None:
        """Stop all active chain runner threads."""
        with cls._lock:
            keys = list(cls._stop_events.keys())
            for stop_event in cls._stop_events.values():
                stop_event.set()
            threads = [(k, cls._threads.get(k)) for k in keys]

        for key, thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=timeout)
