"""View endpoints: pre-composed projections for dashboard, epics, roadmaps, gates, recovery."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB
from pixl_api.helpers import get_or_404

router = APIRouter(prefix="/projects/{project_id}/views", tags=["views"])


def _projection_store(db: ProjectDB):  # noqa: ANN202
    """Instantiate ProjectionStore from the project database."""
    from pixl.storage.db.projections import ProjectionStore

    return ProjectionStore(db)


@router.get("/epics")
async def epic_rollup_list(db: ProjectDB) -> list[dict[str, Any]]:
    """Rollup view of all epics with feature counts and progress."""
    store = _projection_store(db)
    return await asyncio.to_thread(store.epic_rollup)


@router.get("/epics/{epic_id}")
async def epic_rollup_detail(db: ProjectDB, epic_id: str) -> dict[str, Any]:
    """Rollup view for a single epic."""
    store = _projection_store(db)
    results = await asyncio.to_thread(store.epic_rollup, epic_id=epic_id)
    if not results:
        from pixl_api.errors import EntityNotFoundError

        raise EntityNotFoundError("epic", epic_id)
    return results[0]


@router.get("/epics/{epic_id}/features")
async def epic_features(db: ProjectDB, epic_id: str) -> list[dict[str, Any]]:
    """List features belonging to an epic."""
    return await asyncio.to_thread(db.backlog.list_features, epic_id=epic_id)


@router.get("/roadmaps")
async def roadmap_rollup_list(db: ProjectDB) -> list[dict[str, Any]]:
    """Rollup view of all roadmaps with epic/feature counts and progress."""
    store = _projection_store(db)
    return await asyncio.to_thread(store.roadmap_rollup)


@router.get("/gate-inbox")
async def gate_inbox(db: ProjectDB) -> list[dict[str, Any]]:
    """All gates waiting for human approval."""
    store = _projection_store(db)
    return await asyncio.to_thread(store.gate_inbox)


@router.get("/features/{feature_id}")
async def feature_detail(db: ProjectDB, feature_id: str) -> dict[str, Any]:
    """Rich detail view for a single feature."""
    store = _projection_store(db)
    detail = await asyncio.to_thread(store.feature_detail, feature_id)
    return get_or_404(detail, "feature", feature_id)


@router.get("/features/{feature_id}/active-session")
async def feature_active_session(db: ProjectDB, feature_id: str) -> dict[str, Any]:
    """Get the active session for a feature, if any."""
    sessions = await asyncio.to_thread(
        db.sessions.list_sessions, feature_id=feature_id, status="running", limit=1
    )
    if sessions:
        return {"active_session": sessions[0]}
    # Also check waiting_for_gate
    sessions = await asyncio.to_thread(
        db.sessions.list_sessions, feature_id=feature_id, status="waiting_for_gate", limit=1
    )
    if sessions:
        return {"active_session": sessions[0]}
    return {"active_session": None}


@router.get("/recovery-lab")
async def recovery_lab(db: ProjectDB) -> dict[str, Any]:
    """Recovery lab overview: blocked nodes, failure patterns, suggested actions."""
    store = _projection_store(db)
    return await asyncio.to_thread(store.recovery_lab)
