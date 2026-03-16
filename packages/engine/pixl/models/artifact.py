"""Artifact models for workflow outputs.

Artifacts are the outputs of workflow execution - documents, code files,
test results, reviews, etc. Each artifact is tracked with metadata including
hashes for reproducibility and verification.
"""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    """Types of artifacts produced during workflow execution."""

    DOCUMENT = "document"  # Markdown, text, etc.
    CODE = "code"  # Source code files
    TEST = "test"  # Test files
    REVIEW = "review"  # Review documents
    PLAN = "plan"  # Implementation plans
    CONTEXT = "context"  # Context/knowledge documents
    REQUIREMENT = "requirement"  # Requirement analysis
    DIAGRAM = "diagram"  # Diagrams and visual artifacts
    LOG = "log"  # Execution logs
    PROGRESS = "progress"  # Baton progress snapshots from workflow execution
    OTHER = "other"  # Catch-all for other types


class ArtifactMetadata(BaseModel):
    """Metadata for an artifact produced during workflow execution.

    The actual content is stored as a file in the artifacts/ directory.
    This metadata tracks the artifact's identity, type, hashes, and relationships.
    """

    id: str = Field(description="Artifact ID (art-XXXX)")
    type: ArtifactType = Field(description="Type of artifact")
    name: str = Field(description="Artifact filename or identifier")
    path: Path | None = Field(
        default=None, description="Path relative to session artifacts/ folder"
    )

    # Hashes for verification and deduplication
    content_hash: str | None = Field(default=None, description="SHA256 of file content")
    logical_hash: str | None = Field(
        default=None,
        description="Hash of normalized content (whitespace-insensitive)",
    )

    # Provenance
    task_id: str = Field(description="Node ID that produced this artifact")
    session_id: str = Field(description="Session ID")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    # Relationships
    references: list[str] = Field(default_factory=list, description="IDs of related artifacts")
    is_input_for: list[str] = Field(
        default_factory=list, description="IDs of tasks that use this artifact"
    )

    # Additional metadata
    size_bytes: int | None = Field(default=None, description="File size in bytes")
    mime_type: str | None = Field(default=None, description="MIME type if known")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Versioning information
    version: str = Field(default="1.0.0", description="Semantic version string (e.g., '1.0.0')")
    previous_version_id: str | None = Field(
        default=None, description="ID of the previous version of this artifact"
    )
    change_description: str | None = Field(
        default=None, description="Description of changes in this version"
    )

    @property
    def file_path(self) -> Path | None:
        """Alias for path."""
        return self.path

    def add_reference(self, artifact_id: str) -> None:
        """Add a reference to another artifact."""
        if artifact_id not in self.references:
            self.references.append(artifact_id)

    def add_input_for(self, task_id: str) -> None:
        """Mark this artifact as input for a task."""
        if task_id not in self.is_input_for:
            self.is_input_for.append(task_id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactMetadata":
        """Create from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def create(
        cls,
        name: str,
        artifact_type: ArtifactType,
        task_id: str,
        session_id: str,
        content: str | None = None,
        path: Path | None = None,
    ) -> "ArtifactMetadata":
        """Create a new artifact with computed hash.

        Args:
            name: Artifact name
            artifact_type: Type of artifact
            task_id: Node ID that produced this
            session_id: Session ID
            content: Content (for computing hash)
            path: Path to artifact file

        Returns:
            ArtifactMetadata with computed content_hash
        """
        import hashlib
        import uuid

        artifact_id = f"art-{uuid.uuid4().hex[:8]}"
        content_hash = None

        if content:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
        elif path and path.exists():
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        return cls(
            id=artifact_id,
            type=artifact_type,
            name=name,
            path=path,
            content_hash=content_hash,
            task_id=task_id,
            session_id=session_id,
        )


class ArtifactVersion(BaseModel):
    """Represents a specific version of an artifact."""

    id: str = Field(description="Artifact ID for this version")
    version: str = Field(description="Semantic version string")
    content: str | None = Field(default=None, description="Content for this version")
    content_hash: str | None = Field(default=None, description="Content hash")
    change_description: str | None = Field(default=None, description="Description of changes")
    created_at: datetime = Field(description="When this version was created")
    task_id: str = Field(description="Task that created this version")
    session_id: str = Field(description="Session that created this version")


class VersionComparison(BaseModel):
    """Represents a comparison between two versions of an artifact."""

    from_version: str = Field(description="Source version")
    to_version: str = Field(description="Target version")
    from_artifact_id: str = Field(description="ID of source version artifact")
    to_artifact_id: str = Field(description="ID of target version artifact")
    from_content: str | None = Field(default=None, description="Content of source version")
    to_content: str | None = Field(default=None, description="Content of target version")
    line_count_diff: int = Field(
        default=0, description="Difference in line count (positive = lines added)"
    )
    content_changed: bool = Field(
        default=False, description="Whether content changed between versions"
    )
    from_change_description: str | None = Field(
        default=None, description="Change description of source version"
    )
    to_change_description: str | None = Field(
        default=None, description="Change description of target version"
    )
    from_created_at: str | None = Field(
        default=None, description="Creation timestamp of source version"
    )
    to_created_at: str | None = Field(
        default=None, description="Creation timestamp of target version"
    )


class CreateVersionRequest(BaseModel):
    """Request model for creating a new version of an artifact."""

    content: str | None = Field(default=None, description="Updated content")
    version: str | None = Field(
        default=None,
        description="Explicit version string (if None, will auto-increment)",
    )
    change_description: str | None = Field(
        default=None, description="Description of changes in this version"
    )
    bump_type: str = Field(
        default="patch",
        description="Version bump type: 'major', 'minor', or 'patch'",
    )
    tags: list[str] | None = Field(default=None, description="Optional tags")
    extra: dict[str, Any] | None = Field(default=None, description="Additional metadata")

    def validate_bump_type(self) -> "CreateVersionRequest":
        """Validate bump_type field."""
        if self.bump_type not in ("major", "minor", "patch"):
            raise ValueError(
                f"Invalid bump_type: '{self.bump_type}'. Must be one of: 'major', 'minor', 'patch'"
            )
        return self


class VersionListResponse(BaseModel):
    """Response model for listing artifact versions."""

    versions: list[ArtifactVersion] = Field(description="List of artifact versions")
    total_count: int = Field(description="Total number of versions")
    latest_version: str | None = Field(default=None, description="Latest version string")
    artifact_path: str | None = Field(default=None, description="File path of the artifact")
