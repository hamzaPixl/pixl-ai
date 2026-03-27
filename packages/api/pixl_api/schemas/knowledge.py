"""Pydantic request/response models for knowledge endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class SearchResultResponse(BaseModel):
    """Single knowledge search result."""

    source: str
    content: str
    score: float
    chunk_type: str


class KnowledgeStatusResponse(BaseModel):
    """Knowledge index status."""

    files_indexed: int = 0
    chunks: int = 0
    last_build: str | None = None
    index_exists: bool = False
    by_type: dict[str, int] = {}


class BuildRequest(BaseModel):
    """Request body for triggering a knowledge index build."""

    full_rebuild: bool = False
    include_code: bool = False


class ContextRequest(BaseModel):
    """Request body for building a context string."""

    query: str
    max_tokens: int = 4000
    include_source: bool = True
