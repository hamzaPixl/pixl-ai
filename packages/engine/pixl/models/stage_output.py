"""Structured output model for workflow stages.

Replaces free-form markdown with typed JSON inside an XML envelope
(`<pixl_output>{...}</pixl_output>`), validated by JSON Schema.

This makes inter-stage context machine-parseable, token-efficient,
diffable, and fully auditable.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field


class ArtifactWritten(BaseModel):
    """Record of a file written during a stage."""

    path: str = Field(description="Relative path from project root")
    sha256: str = Field(default="", description="SHA256 hex digest of file content")
    purpose: str = Field(description="Short description of this artifact")


class IncludedSource(BaseModel):
    """Record of a source artifact consumed by a stage."""

    artifact_id: str = Field(description="Artifact ID or path")
    sha256: str = Field(default="", description="SHA256 hex digest at read time")
    reason: str = Field(description="Why this source was consumed")


class NextRecommendation(BaseModel):
    """Hint for the next stage in the workflow."""

    recommended_stage: str = Field(description="Suggested next stage ID")
    inputs_needed: list[str] = Field(
        default_factory=list,
        description="Artifacts or data the next stage will need",
    )


class PointerRef(BaseModel):
    """Lightweight reference to heavy content stored elsewhere."""

    ref: str = Field(description="Reference string: artifact:path:sha256:hash")
    stats: dict[str, int] = Field(
        default_factory=dict,
        description="Quick stats about the content (e.g., lines, tokens)",
    )


class StageError(BaseModel):
    """Typed error when status='error'."""

    code: str = Field(default="unknown", description="Machine-readable error code")
    message: str = Field(default="", description="Human-readable error message")
    recoverable: bool = Field(default=True, description="Whether recovery is possible")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context",
    )


class StageOutput(BaseModel):
    """Structured output from a workflow stage.

    Produced inside a `<pixl_output>...</pixl_output>` XML envelope.
    The payload field contains stage-specific structured data.
    """

    schema_version: str = Field(default="1.0", description="Schema version")
    stage_id: str = Field(description="ID of the stage that produced this output")
    status: Literal["ok", "error"] = Field(
        default="ok",
        description="Overall stage result status",
    )
    summary: list[str] = Field(
        default_factory=list,
        description="Up to 10 bullet-point summary items",
    )
    artifacts_written: list[ArtifactWritten] = Field(
        default_factory=list,
        description="Files written during this stage",
    )
    included_sources: list[IncludedSource] = Field(
        default_factory=list,
        description="Source artifacts consumed by this stage",
    )
    next: NextRecommendation | None = Field(
        default=None,
        description="Hint for the next stage",
    )
    error: StageError | None = Field(
        default=None,
        description="Error details when status='error'",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Stage-specific structured data",
    )

    def to_canonical_json(self) -> str:
        """Serialize to canonical JSON (sorted keys, no whitespace).

        Returns:
            Deterministic JSON string suitable for hashing.
        """
        data = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def content_hash(self) -> str:
        """SHA256 of canonical JSON representation.

        Returns:
            Hex digest string.
        """
        canonical = self.to_canonical_json()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "ArtifactWritten",
    "IncludedSource",
    "NextRecommendation",
    "PointerRef",
    "StageError",
    "StageOutput",
]
