"""Knowledge endpoints: search, build, status, context."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from pixl_api.deps import ProjectRoot
from pixl_api.schemas.knowledge import (
    BuildRequest,
    ContextRequest,
    KnowledgeStatusResponse,
    SearchResultResponse,
)

router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["knowledge"])


@router.get("/search", response_model=list[SearchResultResponse])
async def search_knowledge(
    project_root: ProjectRoot,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    scope: str | None = Query(None, description="Scope filter (language, path, glob)"),
    chunk_type: str | None = Query(None, description="Filter by chunk type"),
) -> list[dict[str, Any]]:
    """Full-text search over the knowledge index."""
    from pixl.knowledge.search import KnowledgeSearch
    from pixl.models.knowledge import ChunkType

    ks = KnowledgeSearch(project_root)
    chunk_types_list: list[ChunkType] | None = None
    if chunk_type:
        chunk_types_list = [ChunkType(chunk_type)]
    results = await asyncio.to_thread(
        ks.search, q, limit=limit, chunk_types=chunk_types_list, scope=scope
    )
    return [
        {
            "source": r.chunk.source,
            "content": r.chunk.content,
            "score": r.score,
            "chunk_type": r.chunk.chunk_type.value,
        }
        for r in results
    ]


@router.post("/build")
async def build_index(
    project_root: ProjectRoot,
    body: BuildRequest | None = None,
) -> dict[str, Any]:
    """Trigger a knowledge index rebuild."""
    from pixl.knowledge.indexer import KnowledgeIndex

    req = body or BuildRequest()
    ki = KnowledgeIndex(project_root)
    chunks_created, files_processed = await asyncio.to_thread(
        ki.build, full_rebuild=req.full_rebuild, include_code=req.include_code
    )
    return {
        "chunks_created": chunks_created,
        "files_processed": files_processed,
    }


@router.get("/status", response_model=KnowledgeStatusResponse)
async def get_status(
    project_root: ProjectRoot,
) -> dict[str, Any]:
    """Get knowledge index status."""
    from pixl.knowledge.indexer import KnowledgeIndex

    ki = KnowledgeIndex(project_root)
    status = await asyncio.to_thread(ki.status)
    return {
        "files_indexed": status.get("source_count", 0),
        "chunks": status.get("chunk_count", 0),
        "last_build": status.get("last_build"),
        "index_exists": status.get("index_exists", False),
        "by_type": status.get("by_type", {}),
    }


@router.post("/context")
async def build_context(
    project_root: ProjectRoot,
    body: ContextRequest,
) -> dict[str, str]:
    """Build a context string from relevant knowledge chunks."""
    from pixl.knowledge.context import ContextBuilder

    cb = ContextBuilder(project_root)
    context = await asyncio.to_thread(
        cb.build_context,
        body.query,
        max_tokens=body.max_tokens,
        include_source=body.include_source,
    )
    return {"context": context}
