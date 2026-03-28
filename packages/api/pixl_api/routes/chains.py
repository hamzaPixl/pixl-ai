"""Chain endpoints: list, get, create plan, and start execution."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from pixl_api.deps import ProjectDB
from pixl_api.helpers import get_or_404
from pixl_api.schemas.chains import (
    ChainDetailResponse,
    ChainResponse,
    CreateChainRequest,
    StartChainResponse,
)

router = APIRouter(prefix="/projects/{project_id}/chains", tags=["chains"])


def _get_chain_store(db: ProjectDB):  # noqa: ANN202
    """Instantiate ChainPlanDB from the project database."""
    from pixl.storage.db.chain_plans import ChainPlanDB

    return ChainPlanDB(db)


@router.get("", response_model=list[ChainResponse])
async def list_chains(db: ProjectDB) -> list[dict[str, Any]]:
    """List execution chains for a project."""
    store = _get_chain_store(db)
    return await asyncio.to_thread(store.list_chains)


@router.get("/{chain_id}", response_model=ChainDetailResponse)
async def get_chain(db: ProjectDB, chain_id: str) -> dict[str, Any]:
    """Get full chain detail including nodes and edges."""
    store = _get_chain_store(db)
    detail = await asyncio.to_thread(store.get_chain_detail, chain_id)
    return get_or_404(detail, "chain", chain_id)


@router.post("", response_model=ChainDetailResponse, status_code=501)
async def create_chain(db: ProjectDB, body: CreateChainRequest) -> dict[str, Any]:
    """Create a new chain plan from an epic.

    TODO: Wire to chain planner. Requires epic decomposition into
    features and DAG construction. Currently returns 501.
    """
    # Chain creation requires the full planner pipeline:
    # epic -> feature decomposition -> DAG -> ChainPlanDB insertion.
    # This is orchestrated by the engine's chain planner, not a simple
    # DB insert. Stubbed until the planner is exposed as a callable.
    return {
        "chain_id": "",
        "status": "not_implemented",
        "message": "Chain creation requires engine planner integration",
    }


@router.post("/{chain_id}/start", response_model=StartChainResponse)
async def start_chain(db: ProjectDB, chain_id: str) -> dict[str, Any]:
    """Start execution of a plan_ready chain."""
    store = _get_chain_store(db)
    chain = await asyncio.to_thread(store.get_chain, chain_id)
    get_or_404(chain, "chain", chain_id)

    result = await asyncio.to_thread(store.start_chain, chain_id)
    return {
        "chain_id": chain_id,
        "status": result.get("status", "running"),
        "message": "Chain started",
    }
