"""Artifact lifecycle management for workflow execution.

Extracted from graph_executor.py — handles artifact naming, type inference,
metadata upsert, database persistence, and stage output versioning.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixl.models.session import WorkflowSession
    from pixl.storage import WorkflowSessionStore

logger = logging.getLogger(__name__)

def artifact_name_for_path(
    file_path: Path,
    *,
    artifacts_dir: Path,
    project_root: Path,
) -> str:
    """Compute artifact name relative to artifacts or project root if possible."""
    try:
        artifacts_root = artifacts_dir.resolve()
        return str(file_path.resolve().relative_to(artifacts_root))
    except ValueError:
        try:
            root = project_root.resolve()
            return str(file_path.resolve().relative_to(root))
        except ValueError:
            return file_path.name

def infer_artifact_type(file_path: Path) -> Any:
    """Infer artifact type from filename."""
    from pixl.models.artifact import ArtifactType

    name = file_path.name.lower()
    if "plan" in name:
        return ArtifactType.PLAN
    if "review" in name:
        return ArtifactType.REVIEW
    if "context" in name:
        return ArtifactType.CONTEXT
    if "requirement" in name:
        return ArtifactType.REQUIREMENT
    if "test" in name:
        return ArtifactType.TEST
    if "diagram" in name:
        return ArtifactType.DIAGRAM

    ext = file_path.suffix.lower()
    if ext in {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs"}:
        return ArtifactType.CODE
    if ext in {".md", ".mdx", ".txt"}:
        return ArtifactType.DOCUMENT

    return ArtifactType.OTHER

def upsert_artifact_metadata(
    *,
    artifact_name: str,
    task_id: str,
    content: str,
    version: int,
    session: WorkflowSession,
    artifacts_dir: Path,
    project_root: Path,
    store: WorkflowSessionStore,
) -> None:
    """Create or update artifact metadata in the session and database."""
    from pixl.models.artifact import ArtifactMetadata

    content_hash = hashlib.sha256(content.encode()).hexdigest()
    size_bytes = len(content.encode())
    artifact_type = infer_artifact_type(Path(artifact_name))
    artifact_path = Path(artifact_name)
    existing = next(
        (a for a in session.artifacts if a.get("name") == artifact_name),
        None,
    )
    if existing:
        existing["content_hash"] = content_hash
        existing["size_bytes"] = size_bytes
        existing["task_id"] = task_id
        existing.setdefault("extra", {})
        existing["extra"]["latest_version"] = version
        # Persist each version update for DB-canonical history.
        persist_artifact_to_db(
            artifact_name=artifact_name,
            task_id=task_id,
            content=content,
            artifact_type=existing.get("type") or artifact_type,
            artifact_path=existing.get("path") or artifact_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            latest_version=version,
            session=session,
            store=store,
        )
        return

    meta = ArtifactMetadata.create(
        name=artifact_name,
        artifact_type=artifact_type,
        task_id=task_id,
        session_id=session.id,
        content=content,
        path=artifact_path,
    )
    meta.size_bytes = size_bytes
    meta.extra["latest_version"] = version
    session.add_artifact(meta.to_dict())

    # Also persist to database for searchability and epic linking
    persist_artifact_to_db(
        artifact_name=artifact_name,
        task_id=task_id,
        content=content,
        artifact_type=meta.type,
        artifact_path=meta.path,
        content_hash=meta.content_hash,
        size_bytes=meta.size_bytes,
        latest_version=version,
        session=session,
        store=store,
    )

def persist_artifact_to_db(
    *,
    artifact_name: str,
    task_id: str,
    content: str,
    artifact_type: Any,
    artifact_path: Path | str | None,
    content_hash: str | None,
    size_bytes: int | None,
    latest_version: int | None,
    session: WorkflowSession,
    store: WorkflowSessionStore,
) -> None:
    """Persist artifact to database for searchability and epic linking."""
    try:
        # Determine epic_id from session feature_id
        epic_id = None
        feature_id = session.feature_id
        if (
            feature_id
            and feature_id.startswith("epic-")
            or feature_id
            and not feature_id.startswith("feat-")
        ):
            epic_id = feature_id

        # Infer tags from artifact type and name (deduplicated)
        tags: list[str] = []
        artifact_type_value = (
            artifact_type.value if hasattr(artifact_type, "value") else str(artifact_type)
        )
        if artifact_type_value:
            tags.append(artifact_type_value)
        name_lower = artifact_name.lower()
        for keyword in ("context", "brief", "decomposition", "plan"):
            if keyword in name_lower and keyword not in tags:
                tags.append(keyword)

        store.persist_artifact_record(
            name=artifact_name,
            artifact_type=artifact_type_value,
            task_id=task_id,
            session_id=session.id,
            content=content,
            path=str(artifact_path) if artifact_path else None,
            feature_id=feature_id if feature_id and feature_id.startswith("feat-") else None,
            epic_id=epic_id,
            tags=tags,
            extra={
                "version": latest_version,
                "content_hash": content_hash,
                "size_bytes": size_bytes,
            },
        )

    except Exception as exc:
        logger.warning(f"Failed to persist artifact {artifact_name} to database: {exc}")

def version_stage_outputs(
    *,
    node_id: str,
    stage_configs: dict[str, dict[str, Any]],
    session: WorkflowSession,
    store: WorkflowSessionStore,
    artifacts_dir: Path,
    project_root: Path,
    variables: dict[str, str],
    resolve_template_string: Any,
    emit_error_event: Any,
) -> None:
    """Version stage outputs defined in workflow config."""
    from pixl.errors import StorageError

    stage_config = stage_configs.get(node_id, {})
    outputs = stage_config.get("outputs") or []
    if not outputs:
        return

    for output in outputs:
        resolved = resolve_template_string(output, variables)
        output_path = Path(resolved)
        if not output_path.is_absolute():
            artifact_candidate = artifacts_dir / output_path
            project_candidate = project_root / output_path
            if artifact_candidate.exists() and project_candidate.exists():
                artifact_mtime = artifact_candidate.stat().st_mtime
                project_mtime = project_candidate.stat().st_mtime
                output_path = (
                    artifact_candidate if artifact_mtime >= project_mtime else project_candidate
                )
            elif artifact_candidate.exists():
                output_path = artifact_candidate
            else:
                output_path = project_candidate

        if not output_path.exists() or output_path.is_dir():
            continue

        try:
            content = output_path.read_text(encoding="utf-8")
        except Exception as exc:
            emit_error_event(
                StorageError(
                    "Failed to read artifact for versioning",
                    op="read_artifact_version",
                    details=str(exc),
                    metadata={"path": str(output_path)},
                    cause=exc,
                ),
                node_id=node_id,
            )
            continue

        art_name = artifact_name_for_path(
            output_path,
            artifacts_dir=artifacts_dir,
            project_root=project_root,
        )
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        hash_prefix = content_hash[:12]

        existing = store._get_db().artifacts.get_by_session_path(session.id, art_name)
        if existing:
            if existing.get("content_hash") and existing.get("content_hash", "").startswith(
                hash_prefix
            ):
                continue

        # Save via upsert_artifact_metadata -> persist_artifact_to_db -> store.persist_artifact_record (upsert)
        upsert_artifact_metadata(
            artifact_name=art_name,
            task_id=node_id,
            content=content,
            version=1,
            session=session,
            artifacts_dir=artifacts_dir,
            project_root=project_root,
            store=store,
        )
