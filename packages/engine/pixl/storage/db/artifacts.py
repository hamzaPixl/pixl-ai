"""Artifact store with FTS5 full-text search.

Artifacts are the outputs of workflow execution: plans, code, tests,
reviews, context documents, etc. Storing them with their content
in SQLite makes them RAG-searchable alongside knowledge chunks.

Key design decisions:
- Content stored inline (not just file paths) for searchability
- FTS5 index on name + content + tags for natural language queries
- Linked to features, epics, sessions for provenance tracking
- Content hash for deduplication and integrity verification

THREAD SAFETY: Receives PixlDB and gets thread-local connections
for each operation, making it safe for concurrent use.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
import zlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from pixl.storage.db.base import BaseStore
from pixl.storage.db.fts import prepare_fts_query
from pixl.utils.versioning import (
    VersioningError,
    suggest_next_version,
    version_to_tuple,
)

INLINE_TEXT_THRESHOLD_BYTES = 256 * 1024
CHUNK_SIZE_BYTES = 256 * 1024
MAX_ARTIFACT_SIZE_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class _PreparedContent:
    """Normalized artifact content storage plan."""

    inline_content: str | None
    content_hash: str | None
    size_bytes: int | None
    storage_mode: str
    chunk_count: int
    uncompressed_size_bytes: int | None
    compressed_size_bytes: int | None
    chunks: list[tuple[int, bytes, int]]


class ArtifactDB(BaseStore):
    """Artifact store backed by SQLite with FTS5 search.

    Replaces the file-based artifact storage in session directories
    with a queryable, RAG-friendly database store.

    Receives a PixlDB instance and obtains thread-local connections
    for each operation, making it safe for multi-threaded use.
    """

    # CRUD operations

    def _normalize_session_path(self, logical_path: str) -> str:
        """Normalize and validate session-scoped artifact logical paths."""
        raw = (logical_path or "").strip().replace("\\", "/")
        # Strip sessions/<id>/artifacts/ prefix (agents may use full session path)
        _sessions_prefix = re.match(r"^sessions/[^/]+/artifacts/(.+)$", raw)
        if _sessions_prefix:
            raw = _sessions_prefix.group(1)
        if raw.startswith("artifacts/"):
            raw = raw[len("artifacts/") :]
        if raw.startswith("/"):
            abs_parts = list(PurePosixPath(raw).parts)
            if "artifacts" in abs_parts:
                idx = abs_parts.index("artifacts")
                raw = "/".join(abs_parts[idx + 1 :])
        if not raw:
            raise ValueError("Artifact path cannot be empty")

        path = PurePosixPath(raw)
        if path.is_absolute():
            raise ValueError(f"Artifact path must be relative to session scope: {logical_path}")

        normalized_parts: list[str] = []
        for part in path.parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise ValueError(f"Artifact path traversal is not allowed: {logical_path}")
            normalized_parts.append(part)

        if not normalized_parts:
            raise ValueError(f"Artifact path must contain at least one segment: {logical_path}")
        return "/".join(normalized_parts)

    def _prepare_content(self, content: str | None) -> _PreparedContent:
        """Prepare content for inline/chunked DB storage."""
        if content is None:
            return _PreparedContent(
                inline_content=None,
                content_hash=None,
                size_bytes=None,
                storage_mode="inline",
                chunk_count=0,
                uncompressed_size_bytes=None,
                compressed_size_bytes=None,
                chunks=[],
            )

        encoded = content.encode("utf-8")
        size_bytes = len(encoded)
        if size_bytes > MAX_ARTIFACT_SIZE_BYTES:
            raise ValueError(
                f"Artifact size {size_bytes} exceeds max {MAX_ARTIFACT_SIZE_BYTES} bytes"
            )

        content_hash = hashlib.sha256(encoded).hexdigest()
        if size_bytes <= INLINE_TEXT_THRESHOLD_BYTES:
            return _PreparedContent(
                inline_content=content,
                content_hash=content_hash,
                size_bytes=size_bytes,
                storage_mode="inline",
                chunk_count=0,
                uncompressed_size_bytes=size_bytes,
                compressed_size_bytes=size_bytes,
                chunks=[],
            )

        chunks: list[tuple[int, bytes, int]] = []
        compressed_total = 0
        for idx in range(0, len(encoded), CHUNK_SIZE_BYTES):
            chunk_index = idx // CHUNK_SIZE_BYTES
            raw_chunk = encoded[idx : idx + CHUNK_SIZE_BYTES]
            compressed = zlib.compress(raw_chunk)
            compressed_total += len(compressed)
            chunks.append((chunk_index, compressed, len(raw_chunk)))

        preview = encoded[:INLINE_TEXT_THRESHOLD_BYTES].decode("utf-8", errors="replace")
        return _PreparedContent(
            inline_content=preview,
            content_hash=content_hash,
            size_bytes=size_bytes,
            storage_mode="chunked",
            chunk_count=len(chunks),
            uncompressed_size_bytes=size_bytes,
            compressed_size_bytes=compressed_total,
            chunks=chunks,
        )

    def _materialize_chunks(self, artifact_id: str) -> str | None:
        """Materialize full content from chunk table."""
        rows = self._conn.execute(
            """SELECT chunk_index, payload_compressed
               FROM artifact_chunks
               WHERE artifact_id = ?
               ORDER BY chunk_index ASC""",
            (artifact_id,),
        ).fetchall()
        if not rows:
            return None

        parts: list[bytes] = []
        for row in rows:
            payload = row["payload_compressed"]
            if payload is None:
                continue
            parts.append(zlib.decompress(payload))
        return b"".join(parts).decode("utf-8", errors="replace")

    # Canonical session-scoped operations

    def put(
        self,
        *,
        session_id: str,
        logical_path: str,
        content: str | None,
        artifact_type: str = "other",
        task_id: str = "manual",
        name: str | None = None,
        feature_id: str | None = None,
        epic_id: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
        version: str | None = None,
        previous_version_id: str | None = None,
        change_description: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        """Create a session-scoped artifact with DB-canonical content storage."""
        normalized_path = self._normalize_session_path(logical_path)
        prepared = self._prepare_content(content)
        artifact_id = f"art-{uuid.uuid4().hex[:8]}"
        artifact_name = name or normalized_path

        if version is None:
            version = "1.0.0"
        try:
            version_major, version_minor, version_patch = version_to_tuple(version)
        except VersioningError as e:
            raise ValueError(f"Invalid version format: {e}") from e

        self._conn.execute(
            """INSERT INTO artifacts
               (id, type, name, path, content, content_hash, logical_hash,
                storage_mode, chunk_count, uncompressed_size_bytes, compressed_size_bytes,
                task_id, session_id, feature_id, epic_id,
                size_bytes, mime_type, tags_json, extra_json,
                version, version_major, version_minor, version_patch,
                previous_version_id, change_description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                artifact_id,
                artifact_type,
                artifact_name,
                normalized_path,
                prepared.inline_content,
                prepared.content_hash,
                prepared.content_hash,
                prepared.storage_mode,
                prepared.chunk_count,
                prepared.uncompressed_size_bytes,
                prepared.compressed_size_bytes,
                task_id,
                session_id,
                feature_id,
                epic_id,
                prepared.size_bytes,
                mime_type,
                json.dumps(tags or []),
                json.dumps(extra or {}),
                version,
                version_major,
                version_minor,
                version_patch,
                previous_version_id,
                change_description,
            ),
        )

        if prepared.storage_mode == "chunked":
            self._conn.executemany(
                """INSERT INTO artifact_chunks
                   (artifact_id, chunk_index, payload_compressed, payload_size_bytes)
                   VALUES (?, ?, ?, ?)""",
                [(artifact_id, idx, payload, size) for idx, payload, size in prepared.chunks],
            )

        self._conn.commit()
        return self.get(artifact_id) or {}

    def get_by_session_path(
        self,
        session_id: str,
        logical_path: str,
    ) -> dict[str, Any] | None:
        """Get latest artifact version for a session/path pair."""
        normalized_path = self._normalize_session_path(logical_path)
        row = self._conn.execute(
            """SELECT * FROM artifacts
               WHERE session_id = ? AND path = ?
               ORDER BY version_major DESC, version_minor DESC, version_patch DESC, created_at DESC
               LIMIT 1""",
            (session_id, normalized_path),
        ).fetchone()
        if not row:
            return None
        result = self._row_to_dict(row)
        if result.get("storage_mode") == "chunked":
            result["content"] = self._materialize_chunks(result["id"])
        return result

    def list_page(
        self,
        *,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List artifacts for a session with stable pagination defaults."""
        rows = self._conn.execute(
            """SELECT * FROM artifacts
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (session_id, max(int(limit), 1), max(int(offset), 0)),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search_session(
        self,
        *,
        session_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Session-scoped full-text artifact search."""
        return self.search(query=query, limit=limit, session_id=session_id)

    def materialize(
        self,
        *,
        session_id: str,
        logical_path: str,
    ) -> str | None:
        """Materialize artifact content by session/path (DB-only)."""
        artifact = self.get_by_session_path(session_id, logical_path)
        if artifact is None:
            return None
        return artifact.get("content")

    def create(
        self,
        name: str,
        artifact_type: str,
        task_id: str,
        session_id: str,
        content: str | None = None,
        path: str | None = None,
        feature_id: str | None = None,
        epic_id: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
        version: str | None = None,
        previous_version_id: str | None = None,
        change_description: str | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible create API backed by session-scoped put()."""
        logical_path = path or name
        return self.put(
            session_id=session_id,
            logical_path=logical_path,
            content=content,
            artifact_type=artifact_type,
            task_id=task_id,
            name=name,
            feature_id=feature_id,
            epic_id=epic_id,
            tags=tags,
            extra=extra,
            version=version,
            previous_version_id=previous_version_id,
            change_description=change_description,
        )

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        """Get artifact by ID (materializes chunked content)."""
        row = self._conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        if not row:
            return None
        result = self._row_to_dict(row)
        if result.get("storage_mode") == "chunked":
            result["content"] = self._materialize_chunks(artifact_id)
        return result

    def update(self, artifact_id: str, **fields: Any) -> bool:
        """Update artifact fields."""
        chunks_to_insert: list[tuple[int, bytes, int]] = []
        replace_chunks = False

        if "tags" in fields:
            fields["tags_json"] = json.dumps(fields.pop("tags"))
        if "extra" in fields:
            fields["extra_json"] = json.dumps(fields.pop("extra"))
        if "references" in fields:
            fields["references_json"] = json.dumps(fields.pop("references"))

        if "path" in fields and fields["path"]:
            fields["path"] = self._normalize_session_path(str(fields["path"]))

        if "content" in fields:
            prepared = self._prepare_content(fields.get("content"))
            fields["content"] = prepared.inline_content
            fields["content_hash"] = prepared.content_hash
            fields["logical_hash"] = prepared.content_hash
            fields["size_bytes"] = prepared.size_bytes
            fields["storage_mode"] = prepared.storage_mode
            fields["chunk_count"] = prepared.chunk_count
            fields["uncompressed_size_bytes"] = prepared.uncompressed_size_bytes
            fields["compressed_size_bytes"] = prepared.compressed_size_bytes
            chunks_to_insert = prepared.chunks
            replace_chunks = True

        if not fields:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [artifact_id]
        cursor = self._conn.execute(f"UPDATE artifacts SET {set_clause} WHERE id = ?", values)
        if replace_chunks:
            self._conn.execute("DELETE FROM artifact_chunks WHERE artifact_id = ?", (artifact_id,))
            if chunks_to_insert:
                self._conn.executemany(
                    """INSERT INTO artifact_chunks
                       (artifact_id, chunk_index, payload_compressed, payload_size_bytes)
                       VALUES (?, ?, ?, ?)""",
                    [(artifact_id, idx, payload, size) for idx, payload, size in chunks_to_insert],
                )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, artifact_id: str) -> bool:
        """Delete an artifact."""
        cursor = self._conn.execute("DELETE FROM artifacts WHERE id = ?", (artifact_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    # Query operations

    def list_page_all(self, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List all artifacts with pagination (no session filter)."""
        rows = self._conn.execute(
            """SELECT * FROM artifacts
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (max(int(limit), 1), max(int(offset), 0)),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """List all artifacts for a session."""
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_by_feature(self, feature_id: str) -> list[dict[str, Any]]:
        """List all artifacts for a feature (across all sessions)."""
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE feature_id = ? ORDER BY created_at",
            (feature_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_by_type(
        self, artifact_type: str, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List all artifacts of a specific type with pagination."""
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (artifact_type, max(int(limit), 1), max(int(offset), 0)),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_by_task(self, task_id: str, session_id: str | None = None) -> list[dict[str, Any]]:
        """List artifacts produced by a specific workflow task."""
        where, params = self._build_where({"task_id": task_id, "session_id": session_id})
        rows = self._conn.execute(
            f"SELECT * FROM artifacts {where} ORDER BY created_at", params
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_by_epic(self, epic_id: str) -> list[dict[str, Any]]:
        """List all artifacts for an epic (across all sessions)."""
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE epic_id = ? ORDER BY created_at",
            (epic_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def find_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        """Find artifact by content hash (deduplication)."""
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        ).fetchone()
        return self.get(str(row["id"])) if row else None

    def list_versions_by_path(
        self, path: str, session_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List all versions of an artifact by path with version-aware ordering.

        Args:
            path: File path to find versions for
            session_id: Optional session filter

        Returns:
            List of artifact versions ordered by version (latest first)
        """
        if session_id:
            rows = self._conn.execute(
                """SELECT * FROM artifacts
                   WHERE path = ? AND session_id = ?
                   ORDER BY version_major DESC, version_minor DESC, version_patch DESC""",
                (path, session_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM artifacts
                   WHERE path = ?
                   ORDER BY version_major DESC, version_minor DESC, version_patch DESC""",
                (path,),
            ).fetchall()
        return [self.get(str(r["id"])) or self._row_to_dict(r) for r in rows]

    def get_content(self, artifact_id: str) -> str | None:
        """Get just the content of an artifact.

        More efficient than get() when only content is needed.
        """
        artifact = self.get(artifact_id)
        if artifact is None:
            return None
        return artifact.get("content")

    # Versioning operations

    def create_version(
        self,
        original_artifact_id: str,
        task_id: str,
        session_id: str,
        content: str | None = None,
        version: str | None = None,
        change_description: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new version of an existing artifact.

        Args:
            original_artifact_id: ID of the original artifact to version
            task_id: Workflow node that produced this version
            session_id: Session ID
            content: Updated content for this version
            version: Explicit version string (if None, will auto-increment)
            change_description: Description of changes in this version
            tags: Optional tags for this version
            extra: Additional metadata

        Returns:
            Created version artifact dict

        Raises:
            ValueError: If original artifact not found or version is invalid
        """
        original = self.get(original_artifact_id)
        if not original:
            raise ValueError(f"Original artifact {original_artifact_id} not found")

        # Determine the new version
        if version is None:
            existing_versions = self.get_versions(original_artifact_id)
            version_strings = [v["version"] for v in existing_versions if v.get("version")]
            if not version_strings:
                version = "1.0.1"  # First version after the initial
            else:
                # Auto-increment patch version
                version = suggest_next_version(version_strings, "patch")

        try:
            version_to_tuple(version)
        except VersioningError as e:
            raise ValueError(f"Invalid version format: {e}") from e

        return self.create(
            name=original["name"],
            artifact_type=original["type"],
            task_id=task_id,
            session_id=session_id,
            content=content,
            path=original.get("path"),
            feature_id=original.get("feature_id"),
            epic_id=original.get("epic_id"),
            tags=tags or original.get("tags", []),
            extra=extra or original.get("extra", {}),
            version=version,
            previous_version_id=original_artifact_id,
            change_description=change_description,
        )

    def get_version(self, artifact_id: str, version: str) -> dict[str, Any] | None:
        """Get a specific version of an artifact by its path and version.

        Args:
            artifact_id: ID of any version of the artifact
            version: Version string to retrieve

        Returns:
            Artifact dict for the specified version, or None if not found
        """
        # First get the artifact to find its path
        artifact = self.get(artifact_id)
        if not artifact or not artifact.get("path"):
            return None

        path = artifact["path"]
        version_major, version_minor, version_patch = version_to_tuple(version)

        row = self._conn.execute(
            """SELECT * FROM artifacts
               WHERE path = ? AND version_major = ? AND version_minor = ? AND version_patch = ?
               LIMIT 1""",
            (path, version_major, version_minor, version_patch),
        ).fetchone()

        return self.get(str(row["id"])) if row else None

    def get_versions(self, artifact_id: str) -> list[dict[str, Any]]:
        """Get all versions of an artifact.

        Args:
            artifact_id: ID of any version of the artifact

        Returns:
            List of all versions ordered by version (latest first)
        """
        # First get the artifact to find its path
        artifact = self.get(artifact_id)
        if not artifact or not artifact.get("path"):
            return []

        path = artifact["path"]
        rows = self._conn.execute(
            """SELECT * FROM artifacts
               WHERE path = ?
               ORDER BY version_major DESC, version_minor DESC, version_patch DESC""",
            (path,),
        ).fetchall()

        return [self.get(str(r["id"])) or self._row_to_dict(r) for r in rows]

    def get_latest_version(self, artifact_id: str) -> dict[str, Any] | None:
        """Get the latest version of an artifact.

        Args:
            artifact_id: ID of any version of the artifact

        Returns:
            Latest version artifact dict, or None if not found
        """
        versions = self.get_versions(artifact_id)
        return versions[0] if versions else None

    def compare_versions(
        self, artifact_id: str, from_version: str, to_version: str
    ) -> dict[str, Any] | None:
        """Generate a comparison between two versions of an artifact.

        Args:
            artifact_id: ID of any version of the artifact
            from_version: Source version string
            to_version: Target version string

        Returns:
            Dict with comparison information, or None if versions not found
        """
        from_artifact = self.get_version(artifact_id, from_version)
        to_artifact = self.get_version(artifact_id, to_version)

        if not from_artifact or not to_artifact:
            return None

        # Basic diff information
        from_content = from_artifact.get("content", "")
        to_content = to_artifact.get("content", "")

        # Simple line-based diff count
        from_lines = from_content.splitlines() if from_content else []
        to_lines = to_content.splitlines() if to_content else []

        return {
            "from_version": from_version,
            "to_version": to_version,
            "from_artifact_id": from_artifact["id"],
            "to_artifact_id": to_artifact["id"],
            "from_content": from_content,
            "to_content": to_content,
            "line_count_diff": len(to_lines) - len(from_lines),
            "content_changed": from_content != to_content,
            "from_change_description": from_artifact.get("change_description"),
            "to_change_description": to_artifact.get("change_description"),
            "from_created_at": from_artifact.get("created_at"),
            "to_created_at": to_artifact.get("created_at"),
        }

    def list_versions_by_path_v2(
        self, path: str, session_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Deprecated alias for list_versions_by_path."""
        return self.list_versions_by_path(path, session_id)

    # FTS5 Search (RAG-friendly)

    def search(
        self,
        query: str,
        limit: int = 5,
        artifact_type: str | None = None,
        feature_id: str | None = None,
        epic_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Full-text search across artifact names and content.

        Uses BM25 ranking with column weights:
        - name: 10.0 (most specific)
        - content: 1.0 (broadest)
        - tags: 5.0 (category boosting)

        Args:
            query: Search query (supports FTS5 syntax)
            limit: Max results
            artifact_type: Filter by type
            feature_id: Filter by feature
            epic_id: Filter by epic
            session_id: Filter by session

        Returns:
            Artifacts sorted by relevance with 'score' field.
        """
        if not query.strip():
            return []

        fts_query = prepare_fts_query(query)
        if not fts_query:
            return []

        conditions = []
        params: list[Any] = []

        if artifact_type:
            conditions.append("a.type = ?")
            params.append(artifact_type)
        if feature_id:
            conditions.append("a.feature_id = ?")
            params.append(feature_id)
        if epic_id:
            conditions.append("a.epic_id = ?")
            params.append(epic_id)
        if session_id:
            conditions.append("a.session_id = ?")
            params.append(session_id)

        where_clause = f"AND {' AND '.join(conditions)}" if conditions else ""

        results = self._conn.execute(
            f"""SELECT a.*, bm25(artifacts_fts, 10.0, 1.0, 5.0) as score
                FROM artifacts_fts fts
                JOIN artifacts a ON a.rowid = fts.rowid
                WHERE artifacts_fts MATCH ?
                {where_clause}
                ORDER BY score
                LIMIT ?""",
            (fts_query, *params, limit),
        ).fetchall()

        return [{**self._row_to_dict(r), "score": abs(r["score"])} for r in results]

    def search_for_context(
        self,
        query: str,
        max_tokens: int = 4000,
        artifact_type: str | None = None,
        feature_id: str | None = None,
    ) -> str:
        """Search artifacts and build context string for prompt injection.

        Args:
            query: Search query
            max_tokens: Token budget (1 token ~ 4 chars)
            artifact_type: Optional type filter
            feature_id: Optional feature filter

        Returns:
            Formatted markdown string with relevant artifact content.
        """
        results = self.search(
            query,
            limit=10,
            artifact_type=artifact_type,
            feature_id=feature_id,
        )
        if not results:
            return ""

        sections = ["# Relevant Artifacts\n"]
        token_estimate = 0

        for result in results:
            content = result.get("content", "")
            if not content:
                continue

            # Truncate very long artifacts
            if len(content) > 8000:
                content = content[:8000] + "\n...(truncated)"

            section = f"## {result['name']} ({result['type']})\n{content}\n\n---\n"
            from pixl.utils.tokens import estimate_tokens as _estimate

            tokens = _estimate(section, "markdown")

            if token_estimate + tokens > max_tokens:
                break

            sections.append(section)
            token_estimate += tokens

        return "\n".join(sections)

    # Internal helpers

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert a row to dict with JSON fields deserialized."""
        d = dict(row)
        self._deserialize_json(
            d,
            {
                "tags_json": "tags",
                "extra_json": "extra",
                "references_json": "references",
            },
            defaults={"tags": [], "extra": {}, "references": []},
        )
        return d
