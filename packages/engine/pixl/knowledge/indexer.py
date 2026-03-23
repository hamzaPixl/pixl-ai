"""Build and manage knowledge index using SQLite FTS."""

import hashlib
import json
import time
from pathlib import Path

from pixl.knowledge.chunker import Chunker
from pixl.models.knowledge import Chunk
from pixl.paths import get_pixl_dir
from pixl.storage import create_storage


class KnowledgeIndex:
    """Manages the knowledge index."""

    def __init__(self, project_path: Path, use_ast: bool = True) -> None:
        self.project_path = project_path
        self.source_root = self._resolve_source_root(project_path)
        self.db = create_storage(project_path)
        self.store = self.db.knowledge

        if use_ast:
            try:
                from pixl.knowledge.ast_chunker import ASTChunker

                self.chunker: Chunker = ASTChunker()
            except Exception:
                self.chunker = Chunker()
        else:
            self.chunker = Chunker()

    @staticmethod
    def _resolve_source_root(project_path: Path) -> Path:
        """Resolve the actual source root for file scanning.

        In standalone storage mode, project_path is ~/.pixl/projects/<id>/
        which only contains the DB and sessions. The real source code lives
        at config.json's ``project_root``.
        """
        config_path = project_path / "config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                root = config.get("project_root")
                if root:
                    resolved = Path(root)
                    if resolved.exists():
                        return resolved
            except (json.JSONDecodeError, OSError):
                pass
        return project_path

    def build(
        self,
        full_rebuild: bool = False,
        include_code: bool = False,
    ) -> tuple[int, int]:
        """
        Build or update the knowledge index.

        Args:
            full_rebuild: Force full rebuild even if no changes
            include_code: Also index source code files

        Returns:
            Tuple of (chunks_created, files_processed)
        """
        start_time = time.time()
        source_files = self._collect_source_files(include_code=include_code)

        current_hashes: dict[str, str] = {}
        for file_path in source_files:
            rel_path = str(file_path.relative_to(self.source_root))
            current_hashes[rel_path] = self._file_hash(file_path)

        current_paths = set(current_hashes.keys())
        changed_paths = (
            list(current_paths)
            if full_rebuild
            else self.store.get_changed_documents(current_hashes)
        )

        self.store.remove_stale_documents(current_paths)

        if not changed_paths and not full_rebuild:
            status = self.store.get_status()
            if status.get("chunks", 0) == 0 and source_files:
                changed_paths = list(current_paths)
            else:
                return 0, 0

        chunks_created = 0
        files_processed = 0

        for rel_path in changed_paths:
            file_path = self.source_root / rel_path
            if not file_path.exists():
                continue
            file_hash = current_hashes.get(rel_path) or self._file_hash(file_path)

            doc_id = self.store.upsert_document(rel_path, file_hash)
            chunks = self._chunk_file(file_path)
            chunk_dicts = [self._chunk_to_record(chunk) for chunk in chunks]

            chunks_created += self.store.add_chunks_batch(chunk_dicts, doc_id)
            files_processed += 1

        status = self.store.get_status()
        chunk_count = status.get("chunks", 0)
        source_count = len(current_paths)
        build_duration_ms = int((time.time() - start_time) * 1000)
        self.store.update_manifest(
            chunk_count=chunk_count,
            source_count=source_count,
            build_duration_ms=build_duration_ms,
        )

        return chunks_created, files_processed

    def _collect_source_files(self, include_code: bool = False) -> list[Path]:
        """Collect source files to index.

        Uses ``self.source_root`` (the real project directory) for scanning,
        which may differ from ``self.project_path`` in standalone storage mode.
        """
        root = self.source_root
        docs_dir = root / "docs"
        source_files: list[Path] = []

        if docs_dir.exists():
            source_files.extend(docs_dir.rglob("*.md"))

        for name in ["CLAUDE.md", "README.md", "ARCHITECTURE.md"]:
            root_file = root / name
            if root_file.exists():
                source_files.append(root_file)

        pixl_dir = get_pixl_dir(root)
        try:
            pixl_dir.relative_to(root)
            if pixl_dir.exists():
                source_files.extend(pixl_dir.rglob("*.yaml"))
                source_files.extend(pixl_dir.rglob("*.yml"))
        except ValueError:
            pass

        if include_code:
            code_files: set[Path] = set()
            search_roots = [root / "src", root]
            ignore_dirs = {".pixl", ".git", ".venv", "node_modules", "dist", "build"}

            for search_dir in search_roots:
                if not search_dir.exists():
                    continue
                for ext in self.chunker.config.code_extensions:
                    for path in search_dir.rglob(f"*{ext}"):
                        if any(part in ignore_dirs for part in path.parts):
                            continue
                        code_files.add(path)

            source_files.extend(sorted(code_files))

        return sorted(set(source_files))

    def _file_hash(self, path: Path) -> str:
        """Calculate file hash for change detection."""
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]

    def _chunk_file(self, file_path: Path) -> list[Chunk]:
        """Chunk a file based on its extension."""
        if file_path.suffix in (".md", ".mdx"):
            return self.chunker.chunk_markdown(file_path, self.source_root)
        if file_path.suffix in (".yaml", ".yml"):
            from pixl.knowledge.ast_chunker import ASTChunker

            if isinstance(self.chunker, ASTChunker):
                return self.chunker.chunk_yaml(file_path, self.source_root)
            return self.chunker.chunk_code(file_path, self.source_root)
        return self.chunker.chunk_code(file_path, self.source_root)

    def _chunk_to_record(self, chunk: Chunk) -> dict[str, object]:
        """Convert a Chunk model into a DB record dict."""
        return {
            "id": chunk.id,
            "title": chunk.title,
            "content": chunk.content,
            "source": chunk.source,
            "chunk_type": chunk.chunk_type.value,
            "keywords": chunk.keywords,
            "line_start": chunk.line_start,
            "line_end": chunk.line_end,
        }

    def status(self) -> dict:
        """Get index status."""
        status = self.store.get_status()
        manifest = status.get("manifest") or {}
        by_type = status.get("types") or {}
        chunk_count = status.get("chunks", 0)
        source_count = status.get("documents", 0)

        last_build = manifest.get("last_build") or "Never"
        build_duration = manifest.get("build_duration_ms") or 0

        return {
            "last_build": last_build,
            "chunk_count": chunk_count,
            "source_count": source_count,
            "build_duration_ms": build_duration,
            "by_type": by_type,
            "index_exists": chunk_count > 0,
        }

    def clear(self) -> None:
        """Clear the index."""
        self.store.clear()
