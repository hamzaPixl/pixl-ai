"""Workflow run endpoints: classify prompt, execute with SSE streaming.

Mirrors the CLI's ``_run_workflow_sync`` flow but exposes it over HTTP
with Server-Sent Events for real-time progress.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from pixl_api.deps import CurrentUser, ProjectDB, ProjectRoot
from pixl_api.errors import EntityNotFoundError
from pixl_api.schemas.run import (
    ClassifyRequest,
    ClassifyResponse,
    RunConfirmRequest,
    RunFeatureRequest,
)
from pixl_api.streaming import create_sse_response, workflow_event_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/run", tags=["run"])


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/run  — classify a prompt
# ---------------------------------------------------------------------------


@router.post("", response_model=ClassifyResponse)
async def classify_prompt(
    body: ClassifyRequest,
    project_root: ProjectRoot,
    user: CurrentUser,
) -> dict[str, Any]:
    """Classify a user prompt and return the suggested workflow."""
    # Try LLM-powered classification first, fall back to keyword-based
    try:
        return await _classify_llm(body.prompt, project_root, body.model)
    except Exception:
        logger.debug("LLM classification failed, falling back to keyword classifier", exc_info=True)
        return await asyncio.to_thread(_classify_keyword_fallback, body.prompt, project_root)


async def _classify_llm(prompt: str, project_root: Path, model: str | None) -> dict[str, Any]:
    """LLM-powered classification via PromptClassifier."""
    from pixl.routing.classifier import PromptClassifier

    classifier = PromptClassifier(project_root, model=model)
    router_result = await classifier.classify(prompt)

    return {
        "kind": router_result.kind.value,
        "confidence": router_result.confidence,
        "title": router_result.title,
        "suggested_workflow": router_result.suggested_workflow,
        "estimated_features": router_result.estimated_features,
        "why": router_result.why,
        "risk_flags": router_result.risk_flags,
        "suggested_sub_workflows": router_result.suggested_sub_workflows,
    }


def _classify_keyword_fallback(prompt: str, project_root: Path) -> dict[str, Any]:
    """Keyword-based fallback that returns the full response shape."""
    from pixl.config.workflow_loader import WorkflowLoader
    from pixl.routing.classifier import classify_prompt_fast

    workflow_id = classify_prompt_fast(prompt)

    title = prompt.strip().split("\n")[0][:120]

    kind = "feature"
    if workflow_id in ("roadmap",):
        kind = "roadmap"
    elif workflow_id in ("decompose",):
        kind = "epic"
    elif workflow_id in ("debug",):
        kind = "bug"

    # Verify the workflow exists
    loader = WorkflowLoader(project_root)
    workflows = loader.list_workflows()
    suggested = workflow_id
    for w in workflows:
        if w["id"] == workflow_id:
            break
    else:
        if workflows:
            suggested = workflows[0]["id"]

    return {
        "kind": kind,
        "confidence": None,
        "title": title,
        "suggested_workflow": suggested,
        "estimated_features": 1,
        "why": ["Classified via keyword matching (no LLM provider configured)"],
        "risk_flags": [],
        "suggested_sub_workflows": [],
    }


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/run/confirm  — execute workflow (SSE)
# ---------------------------------------------------------------------------


@router.post("/confirm")
async def run_confirm(
    body: RunConfirmRequest,
    project_root: ProjectRoot,
    db: ProjectDB,
    user: CurrentUser,
) -> StreamingResponse:
    """Execute a workflow from a prompt with SSE streaming.

    1. Creates a backlog feature for the prompt.
    2. Classifies the prompt (or uses explicit workflow_id).
    3. Creates a session and runs the DAG via GraphExecutor.
    4. Streams execution events as SSE ``data:`` lines.

    The final event has ``{"type": "done"}``.
    """
    event_queue: asyncio.Queue[dict] = asyncio.Queue()
    done_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        None,
        _run_workflow_thread,
        body.prompt,
        body.workflow_id,
        body.skip_approval,
        project_root,
        db,
        event_queue,
        done_event,
        None,  # existing_feature_id
        body.kind,
        body.title,
    )

    return create_sse_response(workflow_event_generator(event_queue, done_event))


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/run/feature/{feature_id}  — run existing feature
# ---------------------------------------------------------------------------


@router.post("/feature/{feature_id}")
async def run_feature(
    feature_id: str,
    body: RunFeatureRequest,
    project_root: ProjectRoot,
    db: ProjectDB,
    user: CurrentUser,
) -> StreamingResponse:
    """Execute a workflow for an existing backlog feature (SSE streaming).

    Behaves like ``/confirm`` but skips feature creation and uses the
    existing feature's description as the prompt for classification.
    """
    # Verify feature exists
    feature = await asyncio.to_thread(db.backlog.get_feature, feature_id)
    if feature is None:
        raise EntityNotFoundError("feature", feature_id)

    prompt = feature.get("description") or feature.get("title", "")

    event_queue: asyncio.Queue[dict] = asyncio.Queue()
    done_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        None,
        _run_workflow_thread,
        prompt,
        body.workflow_id,
        body.skip_approval,
        project_root,
        db,
        event_queue,
        done_event,
        feature_id,
        "feature",
        "",
    )

    return create_sse_response(workflow_event_generator(event_queue, done_event))


# ---------------------------------------------------------------------------
# Synchronous workflow execution (runs in a background thread)
# ---------------------------------------------------------------------------


def _put_event(queue: asyncio.Queue[dict], event_data: dict) -> None:
    """Non-blocking put into the async queue from a sync thread."""
    try:
        queue.put_nowait(event_data)
    except Exception:
        pass  # Best-effort — never crash the workflow loop


def _run_workflow_thread(
    prompt: str,
    workflow_id: str | None,
    skip_approval: bool,
    project_root: Path,
    db: Any,
    event_queue: asyncio.Queue[dict],
    done_event: asyncio.Event,
    existing_feature_id: str | None = None,
    kind: str = "feature",
    title: str = "",
) -> None:
    """Execute the full workflow synchronously.

    Adapted from CLI ``_run_workflow_sync``.  Pushes events into
    *event_queue* and sets *done_event* when finished.
    """
    try:
        _run_workflow_inner(
            prompt,
            workflow_id,
            skip_approval,
            project_root,
            db,
            event_queue,
            existing_feature_id,
            kind,
            title,
        )
    except ImportError as exc:
        _put_event(
            event_queue,
            {
                "type": "error",
                "data": {"message": f"Missing dependency: {exc}"},
            },
        )
    except Exception as exc:
        logger.exception("Workflow execution failed")
        _put_event(
            event_queue,
            {
                "type": "error",
                "data": {"message": str(exc)},
            },
        )
    finally:
        done_event.set()


def _run_workflow_inner(
    prompt: str,
    workflow_id: str | None,
    skip_approval: bool,
    project_root: Path,
    db: Any,
    event_queue: asyncio.Queue[dict],
    existing_feature_id: str | None = None,
    kind: str = "feature",
    title: str = "",
) -> None:
    """Core workflow logic — separated for clarity."""
    from pixl.config.workflow_loader import WorkflowLoader
    from pixl.execution import GraphExecutor
    from pixl.execution.workflow_helpers import get_waiting_gate_node, has_waiting_gates
    from pixl.orchestration.core import OrchestratorCore
    from pixl.paths import get_sessions_dir
    from pixl.storage import SessionManager, WorkflowSessionStore

    entity_title = title or prompt[:120]

    # 1. Create or reuse entity based on kind
    if existing_feature_id:
        feature_id = existing_feature_id
        entity_kind = "feature"
        entity_id = feature_id
    elif kind == "roadmap":
        roadmap = db.backlog.add_roadmap(
            title=entity_title,
            original_prompt=prompt,
        )
        entity_id = roadmap["id"]
        entity_kind = "roadmap"
        # Workflows bind to features — create one for execution
        feature = db.backlog.add_feature(
            title=entity_title,
            description=prompt,
            feature_type="feature",
        )
        feature_id = feature["id"]
    elif kind == "epic":
        epic = db.backlog.add_epic(
            title=entity_title,
            original_prompt=prompt,
        )
        entity_id = epic["id"]
        entity_kind = "epic"
        feature = db.backlog.add_feature(
            title=entity_title,
            description=prompt,
            feature_type="feature",
            epic_id=entity_id,
        )
        feature_id = feature["id"]
    else:
        feature = db.backlog.add_feature(
            title=entity_title,
            description=prompt,
            feature_type="feature",
        )
        feature_id = feature["id"]
        entity_id = feature_id
        entity_kind = "feature"

    _put_event(
        event_queue,
        {
            "type": "entity_created",
            "data": {
                "entity_id": entity_id,
                "entity_kind": entity_kind,
                "feature_id": feature_id,
            },
        },
    )

    # 2. Load workflow
    loader = WorkflowLoader(project_root)

    if workflow_id:
        config = loader.load_workflow(workflow_id)
    else:
        from pixl.routing.classifier import classify_prompt_fast

        workflow_id = classify_prompt_fast(prompt)
        config = loader.load_workflow(workflow_id)

    template = loader.convert_to_template(config)
    snapshot = template.current_snapshot

    _put_event(
        event_queue,
        {
            "type": "workflow_loaded",
            "data": {
                "workflow_id": config.id,
                "workflow_name": config.name,
                "version": config.version,
            },
        },
    )

    # 3. Create session
    session_store = WorkflowSessionStore(project_root)
    session = session_store.create_session(feature_id, snapshot)
    session_id = session.id

    _put_event(
        event_queue,
        {
            "type": "session_created",
            "data": {
                "session_id": session_id,
                "entity_id": entity_id,
                "entity_kind": entity_kind,
                "feature_id": feature_id,
            },
        },
    )

    # 4. Set up executor
    session_dir = get_sessions_dir(project_root) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = OrchestratorCore(project_root)
    session_manager = SessionManager(project_root)

    def event_callback(event: Any) -> None:
        """Bridge engine Event objects into the SSE queue."""
        _put_event(
            event_queue,
            {
                "type": "execution_event",
                "event_type": (
                    event.type.value if hasattr(event.type, "value") else str(event.type)
                ),
                "session_id": event.session_id,
                "node_id": event.node_id,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "data": event.data,
            },
        )

    executor = GraphExecutor(
        session,
        snapshot,
        session_dir,
        project_root=project_root,
        orchestrator=orchestrator,
        event_callback=event_callback,
        session_manager=session_manager,
        db=db,
    )

    # 5. Step through the DAG
    step_count = 0
    max_steps = 100

    while step_count < max_steps:
        # Handle waiting gates
        session = executor.session
        if has_waiting_gates(session):
            gate_node_id = get_waiting_gate_node(session)
            if not gate_node_id:
                break

            if skip_approval:
                _put_event(
                    event_queue,
                    {
                        "type": "gate_auto_approved",
                        "data": {"node_id": gate_node_id},
                    },
                )
                session = session_manager.approve_gate(
                    session.id,
                    gate_node_id,
                    approver="auto",
                    snapshot=snapshot,
                )
            else:
                _put_event(
                    event_queue,
                    {
                        "type": "gate_waiting",
                        "data": {"node_id": gate_node_id},
                    },
                )
                break

        result = executor.step()

        if not result["executed"]:
            if result.get("terminal"):
                break
            break

        step_count += 1
        node_id = result.get("node_id", "?")
        _put_event(
            event_queue,
            {
                "type": "step_completed",
                "data": {"step": step_count, "node_id": node_id},
            },
        )

    # 6. Final status
    status_val = session.status
    final_status = status_val.value if hasattr(status_val, "value") else str(status_val)

    _put_event(
        event_queue,
        {
            "type": "workflow_complete",
            "data": {
                "session_id": session_id,
                "entity_id": entity_id,
                "entity_kind": entity_kind,
                "feature_id": feature_id,
                "workflow_id": config.id,
                "status": final_status,
                "steps": step_count,
            },
        },
    )
