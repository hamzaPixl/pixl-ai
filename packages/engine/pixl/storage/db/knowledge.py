"""Knowledge store with FTS5 full-text search.

Implements the SQLite FTS5 knowledge store used by the CLI and API,
providing BM25 ranking, prefix queries, phrase matching,
and column weighting — all built into the database.

The FTS5 tokenizer uses 'porter unicode61' which applies Porter stemming
(so "implementing" matches "implementation") and Unicode-aware tokenization.

Search supports:
- Natural language queries with BM25 ranking
- Column-weighted search (title > keywords > content)
- Chunk type filtering
- Source file filtering
- Phrase matching via double quotes
- Prefix matching via asterisk

THREAD SAFETY: Receives PixlDB and gets thread-local connections
for each operation, making it safe for concurrent use.
"""

from typing import Any

from pixl.storage.db.base import BaseStore
from pixl.storage.db.fts import prepare_fts_query


class KnowledgeDB(BaseStore):
    """Knowledge/RAG store backed by SQLite FTS5.

    Used by:
    - knowledge/indexer.py (index building)
    - knowledge/search.py (search results + ranking)

    Receives a PixlDB instance and obtains thread-local connections
    for each operation, making it safe for multi-threaded use.
    """

    # Document tracking

    def upsert_document(self, path: str, content_hash: str) -> int:
        """Track a source document. Returns document ID.

        If the document already exists with the same hash, returns existing ID.
        If hash differs, updates the hash and returns ID (caller should re-chunk).
        """
        existing = self._conn.execute(
            "SELECT id, content_hash FROM documents WHERE path = ?", (path,)
        ).fetchone()

        if existing:
            if existing["content_hash"] == content_hash:
                return int(existing["id"])
            # Hash changed - update
            self._conn.execute(
                "UPDATE documents SET content_hash = ?, indexed_at = datetime('now') WHERE id = ?",
                (content_hash, existing["id"]),
            )
            return int(existing["id"])

        cursor = self._conn.execute(
            "INSERT INTO documents (path, content_hash) VALUES (?, ?)",
            (path, content_hash),
        )
        return cursor.lastrowid  # type: ignore

    def get_document(self, path: str) -> dict[str, Any] | None:
        """Get document by path."""
        row = self._conn.execute("SELECT * FROM documents WHERE path = ?", (path,)).fetchone()
        return dict(row) if row else None

    def get_changed_documents(self, file_hashes: dict[str, str]) -> list[str]:
        """Find documents that need re-indexing.

        Args:
            file_hashes: {path: sha256_hash} of current files

        Returns:
            List of paths that are new or have changed hashes.
        """
        changed = []
        for path, current_hash in file_hashes.items():
            row = self._conn.execute(
                "SELECT content_hash FROM documents WHERE path = ?", (path,)
            ).fetchone()
            if not row or row["content_hash"] != current_hash:
                changed.append(path)
        return changed

    def remove_stale_documents(self, current_paths: set[str]) -> int:
        """Remove documents that no longer exist on disk.

        Returns count of removed documents. Cascading delete
        removes associated chunks automatically.
        """
        all_docs = self._conn.execute("SELECT id, path FROM documents").fetchall()
        removed = 0
        for doc in all_docs:
            if doc["path"] not in current_paths:
                self._conn.execute("DELETE FROM documents WHERE id = ?", (doc["id"],))
                removed += 1

        if removed:
            self._conn.commit()
        return removed

    # Chunk management

    def add_chunk(
        self,
        chunk_id: str,
        document_id: int,
        title: str,
        content: str,
        source: str,
        chunk_type: str = "concept",
        keywords: list[str] | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
    ) -> None:
        """Add or replace a knowledge chunk.

        The FTS5 index is updated automatically via triggers.
        """
        keyword_str = " ".join(keywords) if keywords else ""

        self._conn.execute(
            """INSERT OR REPLACE INTO chunks
               (id, document_id, title, content, source, chunk_type,
                keywords, line_start, line_end)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chunk_id,
                document_id,
                title,
                content,
                source,
                chunk_type,
                keyword_str,
                line_start,
                line_end,
            ),
        )

    def remove_chunks_for_document(self, document_id: int) -> int:
        """Remove all chunks for a document. Returns count removed."""
        cursor = self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        return cursor.rowcount

    def add_chunks_batch(self, chunks: list[dict[str, Any]], document_id: int) -> int:
        """Bulk insert chunks for a document.

        Removes existing chunks for the document first,
        then inserts all new chunks in a single transaction.
        """
        self.remove_chunks_for_document(document_id)

        for chunk in chunks:
            keywords = chunk.get("keywords", [])
            keyword_str = " ".join(keywords) if isinstance(keywords, list) else keywords

            self._conn.execute(
                """INSERT INTO chunks
                   (id, document_id, title, content, source, chunk_type,
                    keywords, line_start, line_end)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chunk["id"],
                    document_id,
                    chunk["title"],
                    chunk["content"],
                    chunk["source"],
                    chunk.get("chunk_type", "concept"),
                    keyword_str,
                    chunk.get("line_start"),
                    chunk.get("line_end"),
                ),
            )

        self._conn.execute(
            "UPDATE documents SET chunk_count = ? WHERE id = ?",
            (len(chunks), document_id),
        )

        self._conn.commit()
        return len(chunks)

    def list_chunks(self) -> list[dict[str, Any]]:
        """List all chunks in the knowledge store."""
        rows = self._conn.execute(
            "SELECT id, title, content, source, chunk_type, keywords,"
            " line_start, line_end FROM chunks"
        ).fetchall()
        return [
            {
                **dict(r),
                "keywords": r["keywords"].split() if r["keywords"] else [],
            }
            for r in rows
        ]

    # FTS5 Search (replaces custom TF-IDF)

    def search(
        self,
        query: str,
        limit: int = 5,
        chunk_types: list[str] | None = None,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search knowledge chunks using FTS5 BM25 ranking.

        Uses column weighting: title (10.0) > keywords (5.0) > content (1.0)
        This replaces the custom TF-IDF scoring in knowledge/search.py.

        Args:
            query: Natural language search query.
                   Supports FTS5 syntax: "exact phrase", prefix*, AND/OR/NOT.
            limit: Maximum results to return.
            chunk_types: Filter to specific chunk types (concept, procedure, etc.)
            source_filter: Filter to chunks from a specific source path pattern.

        Returns:
            List of chunk dicts with 'score' field (lower = more relevant in BM25).
        """
        if not query.strip():
            return []

        fts_query = prepare_fts_query(query)
        if not fts_query:
            return []

        conditions = []
        params: list[Any] = []

        if chunk_types:
            placeholders = ",".join("?" for _ in chunk_types)
            conditions.append(f"c.chunk_type IN ({placeholders})")
            params.extend(chunk_types)

        if source_filter:
            conditions.append("c.source LIKE ?")
            params.append(f"%{source_filter}%")

        where_clause = f"AND {' AND '.join(conditions)}" if conditions else ""

        # BM25 with column weights: title=10, content=1, keywords=5, source=0.5
        results = self._conn.execute(
            f"""SELECT c.*, bm25(chunks_fts, 10.0, 1.0, 5.0, 0.5) as score
                FROM chunks_fts fts
                JOIN chunks c ON c.rowid = fts.rowid
                WHERE chunks_fts MATCH ?
                {where_clause}
                ORDER BY score
                LIMIT ?""",
            (fts_query, *params, limit),
        ).fetchall()

        return [
            {
                **dict(r),
                "keywords": r["keywords"].split() if r["keywords"] else [],
                "score": abs(r["score"]),  # BM25 returns negative scores
            }
            for r in results
        ]

    def search_for_context(
        self,
        query: str,
        max_tokens: int = 4000,
        chunk_types: list[str] | None = None,
    ) -> str:
        """Search and build a formatted context string for prompt injection.

        Replaces knowledge/context.py's build_context method.

        Args:
            query: Search query
            max_tokens: Approximate token budget (1 token ~ 4 chars)
            chunk_types: Optional chunk type filter

        Returns:
            Formatted markdown string with relevant chunks.
        """
        results = self.search(query, limit=10, chunk_types=chunk_types)
        if not results:
            return ""

        sections = ["# Relevant Project Knowledge\n"]
        token_estimate = 0

        for result in results:
            chunk_text = (
                f"## {result['title']}\n{result['content']}\n_Source: {result['source']}_\n\n---\n"
            )
            from pixl.utils.tokens import estimate_tokens as _estimate

            chunk_tokens = _estimate(chunk_text, "default")

            if token_estimate + chunk_tokens > max_tokens:
                break

            sections.append(chunk_text)
            token_estimate += chunk_tokens

        return "\n".join(sections)

    def search_for_feature(
        self,
        title: str,
        description: str = "",
        max_tokens: int = 3000,
    ) -> str:
        """Build context for a specific feature.

        Replaces knowledge/context.py's build_context_for_feature method.
        """
        query = f"{title} {description}".strip()
        return self.search_for_context(query, max_tokens=max_tokens)

    # Manifest management

    def update_manifest(
        self,
        chunk_count: int,
        source_count: int,
        build_duration_ms: int,
    ) -> None:
        """Update the build manifest (singleton)."""
        self._conn.execute(
            """INSERT INTO knowledge_manifest
               (id, last_build, chunk_count, source_count, build_duration_ms)
               VALUES (1, datetime('now'), ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 last_build = datetime('now'),
                 chunk_count = excluded.chunk_count,
                 source_count = excluded.source_count,
                 build_duration_ms = excluded.build_duration_ms""",
            (chunk_count, source_count, build_duration_ms),
        )
        self._conn.commit()

    def get_manifest(self) -> dict[str, Any] | None:
        """Get the build manifest."""
        row = self._conn.execute("SELECT * FROM knowledge_manifest WHERE id = 1").fetchone()
        return dict(row) if row else None

    def get_status(self) -> dict[str, Any]:
        """Get knowledge index status summary."""
        manifest = self.get_manifest()
        doc_count = self._conn.execute("SELECT COUNT(*) as cnt FROM documents").fetchone()
        chunk_count = self._conn.execute("SELECT COUNT(*) as cnt FROM chunks").fetchone()

        type_counts = self._conn.execute(
            "SELECT chunk_type, COUNT(*) as cnt FROM chunks GROUP BY chunk_type"
        ).fetchall()

        return {
            "documents": doc_count["cnt"] if doc_count else 0,
            "chunks": chunk_count["cnt"] if chunk_count else 0,
            "types": {r["chunk_type"]: r["cnt"] for r in type_counts},
            "manifest": manifest,
        }

    def clear(self) -> None:
        """Clear all knowledge data."""
        self._conn.execute("DELETE FROM chunks")
        self._conn.execute("DELETE FROM documents")
        self._conn.execute("DELETE FROM knowledge_manifest")
        self._conn.commit()
