"""Knowledge system models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ChunkType(StrEnum):
    """Type of knowledge chunk."""

    CONCEPT = "concept"  # What is X?
    PROCEDURE = "procedure"  # How to do X
    REFERENCE = "reference"  # API/config reference
    CODE = "code"  # Code example


class Chunk(BaseModel):
    """A single knowledge chunk."""

    id: str = Field(description="Unique chunk ID")
    title: str = Field(description="Chunk title/header")
    content: str = Field(description="Chunk content (max 2000 chars)")
    source: str = Field(description="Source file path")
    chunk_type: ChunkType = Field(default=ChunkType.CONCEPT)
    keywords: list[str] = Field(default_factory=list)
    line_start: int | None = Field(default=None)
    line_end: int | None = Field(default=None)


class KnowledgeManifest(BaseModel):
    """Build manifest for incremental updates."""

    version: str = "1.0"
    last_build: datetime | None = None
    chunk_count: int = 0
    source_count: int = 0
    file_hashes: dict[str, str] = Field(default_factory=dict)
    build_duration_ms: int = 0


class SearchResult(BaseModel):
    """A search result with scoring."""

    chunk: Chunk
    score: float
    matched_terms: list[str]
