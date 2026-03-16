"""Baton patch application and progress artifact persistence.

Extracted from graph_executor.py — handles extracting baton patches from
agent output, applying them to the session baton, and persisting progress
artifacts for subsequent stages.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixl.models.session import WorkflowSession
    from pixl.storage import WorkflowSessionStore

logger = logging.getLogger(__name__)


def apply_baton_patch(
    session: WorkflowSession,
    result_text: str,
    node_id: str,
    stage_output: Any | None = None,
) -> None:
    """Extract and apply baton patch from agent output.

    Looks for baton_patch in the payload.baton_patch field inside the
    <pixl_output> envelope.

    Applies the patch to the session baton.

    Args:
        session: Workflow session
        result_text: Agent result text.
        node_id: Current node ID (for history tracking).
        stage_output: Pre-extracted StageOutput (avoids re-parsing the envelope).
    """
    from pixl.models.baton import Baton

    if session.baton is None:
        return

    patch = None

    # Use pre-extracted stage_output if provided (avoids double extraction)
    if stage_output is not None:
        payload = getattr(stage_output, "payload", None)
        if payload:
            patch = payload.get("baton_patch")
    else:
        # Fallback: extract from envelope when stage_output not provided
        try:
            from pixl.execution.envelope import extract_envelope

            extracted, _ = extract_envelope(result_text)
            if extracted and extracted.payload:
                patch = extracted.payload.get("baton_patch")
        except Exception:
            logger.debug("Envelope extraction for baton patch failed", exc_info=True)

    if patch is None:
        return

    try:
        baton = Baton.from_dict(session.baton)
        updated = baton.apply_patch(patch)
        session.baton = updated.model_dump()

        # Record snapshot in history (cap at last 5 to limit serialization growth)
        session.baton_history.append(
            {
                "stage_id": node_id,
                "timestamp": datetime.now().isoformat(),
                "baton": updated.model_dump(),
                "patch_applied": patch,
            }
        )
        if len(session.baton_history) > 5:
            session.baton_history = session.baton_history[-5:]
    except Exception as exc:
        logger.warning("Failed to apply baton patch at %s: %s", node_id, exc)


def persist_progress_artifact(
    session: WorkflowSession,
    node_id: str,
    artifacts_dir: Path,
    store: WorkflowSessionStore | None = None,
) -> None:
    """Write a progress artifact from the current baton state.

    This persists the baton snapshot as a ``progress`` artifact so that
    it survives context compaction and is available to the unified
    compiler for subsequent stages.

    Args:
        session: Workflow session
        node_id: Current node ID
        artifacts_dir: Directory for artifact storage
    """
    try:
        if session.baton is None:
            return
        from pixl.models.baton import Baton

        baton = Baton.from_dict(session.baton)
        content = baton.to_prompt_section()
        if not content:
            return

        artifact_name = f"progress-{node_id}.md"
        if store is not None:
            store.save_artifact(session.id, artifact_name, content)
            return
        artifact_path = artifacts_dir / artifact_name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
    except Exception as exc:
        logger.debug("Progress artifact persistence failed at %s: %s", node_id, exc)
