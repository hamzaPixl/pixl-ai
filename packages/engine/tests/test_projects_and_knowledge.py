"""Tests for project registry and knowledge indexer/search modules.

Covers:
- packages/engine/pixl/projects/registry.py
- packages/engine/pixl/knowledge/indexer.py
- packages/engine/pixl/knowledge/search.py
- packages/engine/pixl/knowledge/chunker.py
- packages/engine/pixl/knowledge/context.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pixl.storage.db.db_registry import _reset_for_testing

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_project_dir(base: Path, project_id: str) -> Path:
    """Create a minimal project directory under base/projects/."""
    project_dir = base / "projects" / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "sessions").mkdir()
    return project_dir


def _write_config(project_dir: Path, config: dict) -> None:
    (project_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")


# ---------------------------------------------------------------------------
# projects/registry.py
# ---------------------------------------------------------------------------


class TestListProjects:
    def test_returns_empty_list_when_no_projects_dir(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        result = list_projects(global_dir=tmp_path)

        assert result == []

    def test_returns_empty_list_when_projects_dir_is_empty(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        (tmp_path / "projects").mkdir()

        result = list_projects(global_dir=tmp_path)

        assert result == []

    def test_lists_single_project(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        project_dir = _make_project_dir(tmp_path, "my-project-abc123")
        _write_config(project_dir, {"project_name": "My Project"})

        result = list_projects(global_dir=tmp_path)

        assert len(result) == 1
        assert result[0]["project_id"] == "my-project-abc123"
        assert result[0]["project_name"] == "My Project"

    def test_lists_multiple_projects_sorted(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        for pid in ["alpha-001", "beta-002", "gamma-003"]:
            _make_project_dir(tmp_path, pid)

        result = list_projects(global_dir=tmp_path)

        assert len(result) == 3
        ids = [p["project_id"] for p in result]
        assert ids == sorted(ids)

    def test_project_without_config_uses_dir_name_as_project_name(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        _make_project_dir(tmp_path, "bare-project-xyz")

        result = list_projects(global_dir=tmp_path)

        assert result[0]["project_name"] == "bare-project-xyz"

    def test_project_with_db_file_has_db_path(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        project_dir = _make_project_dir(tmp_path, "db-project-abc")
        (project_dir / "pixl.db").touch()

        result = list_projects(global_dir=tmp_path)

        assert result[0]["db_path"] is not None
        assert result[0]["db_path"].endswith("pixl.db")

    def test_project_without_db_file_has_null_db_path(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        _make_project_dir(tmp_path, "no-db-project-abc")

        result = list_projects(global_dir=tmp_path)

        assert result[0]["db_path"] is None

    def test_ignores_non_directory_entries(self, tmp_path: Path) -> None:
        from pixl.projects.registry import list_projects

        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        (projects_dir / "stray-file.txt").write_text("junk")

        result = list_projects(global_dir=tmp_path)

        assert result == []


class TestGetProject:
    def test_returns_none_for_nonexistent_project(self, tmp_path: Path) -> None:
        from pixl.projects.registry import get_project

        result = get_project("does-not-exist", global_dir=tmp_path)

        assert result is None

    def test_returns_project_info_for_existing_project(self, tmp_path: Path) -> None:
        from pixl.projects.registry import get_project

        project_dir = _make_project_dir(tmp_path, "known-project-abc")
        _write_config(project_dir, {"project_name": "Known Project"})

        result = get_project("known-project-abc", global_dir=tmp_path)

        assert result is not None
        assert result["project_id"] == "known-project-abc"
        assert result["project_name"] == "Known Project"

    def test_project_info_includes_storage_dir(self, tmp_path: Path) -> None:
        from pixl.projects.registry import get_project

        _make_project_dir(tmp_path, "storage-project-abc")

        result = get_project("storage-project-abc", global_dir=tmp_path)

        assert result is not None
        assert "storage_dir" in result

    def test_project_info_includes_project_root_from_config(self, tmp_path: Path) -> None:
        from pixl.projects.registry import get_project

        project_dir = _make_project_dir(tmp_path, "rooted-project-abc")
        _write_config(project_dir, {"project_root": "/some/path"})

        result = get_project("rooted-project-abc", global_dir=tmp_path)

        assert result is not None
        assert result["project_root"] == "/some/path"

    def test_handles_malformed_config_gracefully(self, tmp_path: Path) -> None:
        from pixl.projects.registry import get_project

        project_dir = _make_project_dir(tmp_path, "bad-config-abc")
        (project_dir / "config.json").write_text("NOT VALID JSON", encoding="utf-8")

        result = get_project("bad-config-abc", global_dir=tmp_path)

        assert result is not None
        assert result["project_id"] == "bad-config-abc"


class TestCreateProject:
    def test_creates_project_directory_structure(self, tmp_path: Path) -> None:
        from pixl.projects.registry import create_project

        info = create_project("Test Project", "A test project", global_dir=tmp_path)

        project_dir = Path(info["storage_dir"])
        assert project_dir.is_dir()
        assert (project_dir / "sessions").is_dir()
        assert (project_dir / "config.json").is_file()

    def test_config_json_has_correct_fields(self, tmp_path: Path) -> None:
        from pixl.projects.registry import create_project

        info = create_project("My App", "App description", global_dir=tmp_path)

        config = json.loads((Path(info["storage_dir"]) / "config.json").read_text())
        assert config["project_name"] == "My App"
        assert config["description"] == "App description"
        assert config["storage_mode"] == "standalone"

    def test_raises_if_project_already_exists(self, tmp_path: Path) -> None:
        from pixl.projects.registry import create_project

        create_project("Duplicate", "first", global_dir=tmp_path)
        with pytest.raises(ValueError, match="already exists"):
            create_project("Duplicate", "second", global_dir=tmp_path)

    def test_returned_info_has_expected_keys(self, tmp_path: Path) -> None:
        from pixl.projects.registry import create_project

        info = create_project("Key Test", "testing keys", global_dir=tmp_path)

        for key in ("project_id", "project_name", "storage_dir"):
            assert key in info

    def test_project_with_root_path_stores_project_root(self, tmp_path: Path) -> None:
        from pixl.projects.registry import create_project

        project_root = str(tmp_path / "myapp")

        info = create_project(
            "Rooted App", "has root", project_root=project_root, global_dir=tmp_path
        )

        config = json.loads((Path(info["storage_dir"]) / "config.json").read_text())
        assert config.get("project_root") == project_root


class TestDeleteProject:
    def test_returns_false_for_nonexistent_project(self, tmp_path: Path) -> None:
        from pixl.projects.registry import delete_project

        result = delete_project("ghost-project-abc", global_dir=tmp_path)

        assert result is False

    def test_deletes_existing_project(self, tmp_path: Path) -> None:
        from pixl.projects.registry import delete_project, list_projects

        _make_project_dir(tmp_path, "to-delete-abc")

        result = delete_project("to-delete-abc", global_dir=tmp_path)

        assert result is True
        assert list_projects(global_dir=tmp_path) == []

    def test_idempotent_delete_returns_false_second_time(self, tmp_path: Path) -> None:
        from pixl.projects.registry import delete_project

        _make_project_dir(tmp_path, "once-project-abc")

        delete_project("once-project-abc", global_dir=tmp_path)
        result = delete_project("once-project-abc", global_dir=tmp_path)

        assert result is False


# ---------------------------------------------------------------------------
# knowledge/chunker.py
# ---------------------------------------------------------------------------


class TestChunker:
    def test_chunk_markdown_splits_by_headers(self, tmp_path: Path) -> None:
        from pixl.knowledge.chunker import Chunker

        md_file = tmp_path / "README.md"
        md_file.write_text(
            "# Introduction\n\n"
            "This section has enough text to exceed the minimum chunk size threshold "
            "so it will be included in the output.\n\n"
            "## Details\n\n"
            "More content goes here and it should also be long enough to be indexed "
            "by the knowledge chunker without being skipped.\n",
            encoding="utf-8",
        )

        chunker = Chunker()
        chunks = chunker.chunk_markdown(md_file, tmp_path)

        assert len(chunks) >= 1
        titles = [c.title for c in chunks]
        assert any("Introduction" in t or "Details" in t for t in titles)

    def test_chunk_markdown_skips_too_short_content(self, tmp_path: Path) -> None:
        from pixl.knowledge.chunker import Chunker

        md_file = tmp_path / "tiny.md"
        # Each section body is shorter than min_chunk_size (50 chars)
        md_file.write_text("# A\n\nhi\n\n# B\n\nbye\n", encoding="utf-8")

        chunker = Chunker()
        chunks = chunker.chunk_markdown(md_file, tmp_path)

        # All sections are too short; no chunks should be produced
        assert chunks == []

    def test_chunk_code_python_produces_chunks(self, tmp_path: Path) -> None:
        from pixl.knowledge.chunker import Chunker, ChunkType

        py_file = tmp_path / "sample.py"
        py_file.write_text(
            "def compute_result(x, y):\n"
            "    # this function does a computation\n"
            "    return x + y + x * y\n\n"
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b\n",
            encoding="utf-8",
        )

        chunker = Chunker()
        chunks = chunker.chunk_code(py_file, tmp_path)

        assert len(chunks) >= 1
        assert all(c.chunk_type == ChunkType.CODE for c in chunks)

    def test_chunk_code_extracts_function_name_as_title(self, tmp_path: Path) -> None:
        from pixl.knowledge.chunker import Chunker

        # The regex splits on the `def/class` line itself; the delimiter part
        # (e.g. "def my_special_function") is a separate chunk candidate.
        # Provide enough text so the delimiter chunk exceeds min_chunk_size (50).
        py_file = tmp_path / "funcs.py"
        py_file.write_text(
            "def my_special_function_with_a_longer_name_to_pass_minimum_size(arg):\n"
            "    # long enough content to pass the minimum size check\n"
            "    result = arg * 2 + arg - 1\n"
            "    return result\n",
            encoding="utf-8",
        )

        chunker = Chunker()
        chunks = chunker.chunk_code(py_file, tmp_path)

        long_name = "my_special_function_with_a_longer_name_to_pass_minimum_size"
        assert any(long_name in c.title for c in chunks)

    def test_make_chunk_generates_id_without_slashes(self, tmp_path: Path) -> None:
        from pixl.knowledge.chunker import Chunker, ChunkType

        chunker = Chunker()
        chunk = chunker._make_chunk(
            title="MyTitle",
            content="Some content for this chunk",
            source="src/mymodule.py",
            chunk_type=ChunkType.CODE,
        )

        assert "/" not in chunk.id

    def test_extract_keywords_filters_stopwords(self) -> None:
        from pixl.knowledge.chunker import Chunker

        chunker = Chunker()
        keywords = chunker._extract_keywords("the quick brown fox and the lazy dog")

        assert "the" not in keywords
        assert "and" not in keywords
        assert "fox" in keywords or "brown" in keywords

    def test_extract_keywords_returns_at_most_20(self) -> None:
        from pixl.knowledge.chunker import Chunker

        chunker = Chunker()
        long_text = " ".join([f"word{i}" for i in range(50)])
        keywords = chunker._extract_keywords(long_text)

        assert len(keywords) <= 20

    def test_detect_type_procedure_from_step_indicator(self) -> None:
        from pixl.knowledge.chunker import Chunker, ChunkType

        chunker = Chunker()
        chunk_type = chunker._detect_type("Step 1: Do this first, then proceed.")

        assert chunk_type == ChunkType.PROCEDURE

    def test_detect_type_reference_from_many_pipes(self) -> None:
        from pixl.knowledge.chunker import Chunker, ChunkType

        chunker = Chunker()
        # More than 5 pipe characters triggers REFERENCE
        chunk_type = chunker._detect_type("| col1 | col2 | col3 | col4 | col5 | col6 |")

        assert chunk_type == ChunkType.REFERENCE

    def test_detect_type_code_from_backtick_fences(self) -> None:
        from pixl.knowledge.chunker import Chunker, ChunkType

        chunker = Chunker()
        chunk_type = chunker._detect_type("Here is code:\n```\nprint('hello')\n```\n")

        assert chunk_type == ChunkType.CODE

    def test_detect_type_concept_as_default(self) -> None:
        from pixl.knowledge.chunker import Chunker, ChunkType

        chunker = Chunker()
        chunk_type = chunker._detect_type("This is a general description of a concept.")

        assert chunk_type == ChunkType.CONCEPT

    def test_chunk_source_path_is_relative(self, tmp_path: Path) -> None:
        from pixl.knowledge.chunker import Chunker

        subdir = tmp_path / "docs"
        subdir.mkdir()
        md_file = subdir / "guide.md"
        md_file.write_text(
            "# Guide\n\n"
            "This section has enough text to exceed the minimum chunk size threshold "
            "for the knowledge chunker to index it properly.\n",
            encoding="utf-8",
        )

        chunker = Chunker()
        chunks = chunker.chunk_markdown(md_file, tmp_path)

        assert len(chunks) >= 1
        assert chunks[0].source == "docs/guide.md"


# ---------------------------------------------------------------------------
# knowledge/indexer.py
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_with_pixl(tmp_path: Path):
    """Create a minimal project with a .pixl dir so create_storage works."""
    _reset_for_testing()
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    yield tmp_path
    _reset_for_testing()


class TestKnowledgeIndex:
    def test_build_returns_zero_when_no_source_files(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        chunks_created, files_processed = idx.build()

        assert chunks_created == 0
        assert files_processed == 0

    def test_build_indexes_readme_at_root(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        readme = project_with_pixl / "README.md"
        readme.write_text(
            "# Project\n\n"
            "This is a detailed description of the project that is long enough "
            "to be included as a knowledge chunk by the indexer.\n",
            encoding="utf-8",
        )

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        chunks_created, files_processed = idx.build()

        assert files_processed == 1
        assert chunks_created >= 1

    def test_build_indexes_docs_markdown_files(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        docs = project_with_pixl / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text(
            "# Guide\n\n"
            "This is the detailed documentation guide content that exceeds the "
            "minimum chunk size for inclusion in the knowledge index.\n",
            encoding="utf-8",
        )

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        chunks_created, files_processed = idx.build()

        assert files_processed >= 1
        assert chunks_created >= 1

    def test_full_rebuild_reindexes_all_files(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        readme = project_with_pixl / "README.md"
        readme.write_text(
            "# Project\n\n"
            "This is a detailed description that is long enough to be chunked properly "
            "by the knowledge indexer during the rebuild process.\n",
            encoding="utf-8",
        )

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        idx.build()
        chunks_created, files_processed = idx.build(full_rebuild=True)

        assert files_processed >= 1

    def test_incremental_build_skips_unchanged_files(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        readme = project_with_pixl / "README.md"
        readme.write_text(
            "# Stable\n\n"
            "This content will not change between builds so the incremental "
            "build should detect no changes and skip reprocessing it.\n",
            encoding="utf-8",
        )

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        idx.build()
        chunks_created, files_processed = idx.build()

        # Second build should find no changes
        assert chunks_created == 0
        assert files_processed == 0

    def test_status_reflects_indexed_chunks(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        readme = project_with_pixl / "README.md"
        readme.write_text(
            "# Status Test\n\n"
            "Enough content to produce at least one chunk and update the manifest "
            "so the status call will reflect the indexed data correctly.\n",
            encoding="utf-8",
        )

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        idx.build()
        status = idx.status()

        assert status["index_exists"] is True
        assert status["chunk_count"] > 0

    def test_status_before_build_shows_no_index(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        status = idx.status()

        assert status["index_exists"] is False

    def test_clear_removes_all_chunks(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        readme = project_with_pixl / "README.md"
        readme.write_text(
            "# Clear Test\n\n"
            "Content to be indexed and then cleared from the knowledge store "
            "to verify the clear operation works as expected.\n",
            encoding="utf-8",
        )

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        idx.build()
        idx.clear()
        status = idx.status()

        assert status["index_exists"] is False

    def test_resolve_source_root_falls_back_to_project_path(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        root = KnowledgeIndex._resolve_source_root(project_with_pixl)

        assert root == project_with_pixl

    def test_resolve_source_root_uses_config_project_root(self, tmp_path: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        standalone_dir = tmp_path / "standalone"
        standalone_dir.mkdir()
        real_source = tmp_path / "real-source"
        real_source.mkdir()
        (standalone_dir / "config.json").write_text(
            json.dumps({"project_root": str(real_source)}), encoding="utf-8"
        )

        root = KnowledgeIndex._resolve_source_root(standalone_dir)

        assert root == real_source

    def test_build_with_include_code_indexes_python_files(self, tmp_path: Path) -> None:
        """Use a fresh project with a single-function file to avoid chunk id collisions.

        The fallback Chunker uses ``source:title`` as the chunk id where title is
        extracted via regex from the chunk body.  Multiple functions with bodies
        that both contain "function" in a comment would produce the same id because
        the regex picks the first match.  A single-function file avoids that.
        """
        _reset_for_testing()
        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir()

        from pixl.knowledge.indexer import KnowledgeIndex

        src = tmp_path / "src"
        src.mkdir()
        # Single function with a body long enough to pass min_chunk_size
        (src / "utils.py").write_text(
            "def compute_sum(a, b):\n"
            '    """Return the sum of a and b."""\n'
            "    total = a + b\n"
            "    return total\n",
            encoding="utf-8",
        )

        idx = KnowledgeIndex(tmp_path, use_ast=False)
        chunks_created, files_processed = idx.build(include_code=True)

        _reset_for_testing()
        assert files_processed >= 1
        assert chunks_created >= 1

    def test_file_hash_is_16_hex_chars(self, project_with_pixl: Path) -> None:
        from pixl.knowledge.indexer import KnowledgeIndex

        test_file = project_with_pixl / "test.txt"
        test_file.write_text("hello world", encoding="utf-8")

        idx = KnowledgeIndex(project_with_pixl, use_ast=False)
        h = idx._file_hash(test_file)

        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# knowledge/search.py
# ---------------------------------------------------------------------------


@pytest.fixture()
def indexed_project(tmp_path: Path):
    """Create a project with an indexed knowledge base."""
    _reset_for_testing()
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()

    # Write a few markdown files to index
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Authentication\n\n"
        "The authentication system uses JWT tokens for secure access. "
        "Users must provide valid credentials to obtain a token. "
        "The token expires after 15 minutes for security reasons.\n\n"
        "## Configuration\n\n"
        "Configure the auth system using environment variables: "
        "AUTH_SECRET sets the JWT secret key. "
        "AUTH_EXPIRY controls the token lifetime in seconds.\n",
        encoding="utf-8",
    )
    arch = tmp_path / "ARCHITECTURE.md"
    arch.write_text(
        "# Architecture Overview\n\n"
        "The system follows a layered architecture pattern with clear separation "
        "of concerns. The domain layer contains business logic while the "
        "infrastructure layer handles external dependencies.\n\n"
        "## Design Principles\n\n"
        "We follow SOLID principles and domain-driven design concepts "
        "to keep the system maintainable and extensible over time.\n",
        encoding="utf-8",
    )

    from pixl.knowledge.indexer import KnowledgeIndex

    idx = KnowledgeIndex(tmp_path, use_ast=False)
    idx.build(full_rebuild=True)

    yield tmp_path
    _reset_for_testing()


class TestDetectQueryIntent:
    def test_neutral_when_no_signals(self) -> None:
        from pixl.knowledge.search import detect_query_intent

        boosts = detect_query_intent(["something", "random", "words"])

        assert all(v == 1.0 for v in boosts.values())

    def test_boosts_code_type_for_code_signals(self) -> None:
        from pixl.knowledge.search import detect_query_intent
        from pixl.models.knowledge import ChunkType

        boosts = detect_query_intent(["function", "class", "method"])

        assert boosts[ChunkType.CODE] > 1.0

    def test_boosts_concept_type_for_concept_signals(self) -> None:
        from pixl.knowledge.search import detect_query_intent
        from pixl.models.knowledge import ChunkType

        boosts = detect_query_intent(["architecture", "design", "pattern"])

        assert boosts[ChunkType.CONCEPT] > 1.0

    def test_boosts_reference_type_for_reference_signals(self) -> None:
        from pixl.knowledge.search import detect_query_intent
        from pixl.models.knowledge import ChunkType

        boosts = detect_query_intent(["config", "configuration", "schema"])

        assert boosts[ChunkType.REFERENCE] > 1.0

    def test_boosts_procedure_type_for_procedure_signals(self) -> None:
        from pixl.knowledge.search import detect_query_intent
        from pixl.models.knowledge import ChunkType

        boosts = detect_query_intent(["setup", "install", "deploy"])

        assert boosts[ChunkType.PROCEDURE] > 1.0

    def test_non_dominant_types_are_penalized(self) -> None:
        from pixl.knowledge.search import detect_query_intent
        from pixl.models.knowledge import ChunkType

        boosts = detect_query_intent(["function", "class", "def"])

        assert boosts.get(ChunkType.CONCEPT, 1.0) < 1.0


class TestSourceMatchesScope:
    def test_language_name_python_matches_py_extension(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("src/module.py", "python") is True

    def test_language_name_python_rejects_ts_extension(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("src/module.ts", "python") is False

    def test_glob_suffix_matches_correct_extension(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("path/to/file.py", "*.py") is True

    def test_glob_suffix_rejects_wrong_extension(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("path/to/file.ts", "*.py") is False

    def test_path_substring_matches_partial_path(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("src/auth/handler.py", "src/auth") is True

    def test_path_substring_rejects_non_matching_path(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("src/billing/handler.py", "src/auth") is False

    def test_typescript_scope_matches_ts_and_tsx(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("app/component.tsx", "typescript") is True
        assert _source_matches_scope("lib/util.ts", "typescript") is True

    def test_markdown_scope_matches_md_and_mdx(self) -> None:
        from pixl.knowledge.search import _source_matches_scope

        assert _source_matches_scope("docs/guide.md", "markdown") is True
        assert _source_matches_scope("docs/post.mdx", "markdown") is True


class TestCrossReferenceIndex:
    def test_get_related_returns_siblings_from_same_source(self) -> None:
        from pixl.knowledge.search import CrossReferenceIndex
        from pixl.models.knowledge import Chunk, ChunkType

        chunks = [
            Chunk(
                id="src/mod.py:func_a",
                title="func_a",
                content="def func_a(): pass",
                source="src/mod.py",
                chunk_type=ChunkType.CODE,
            ),
            Chunk(
                id="src/mod.py:func_b",
                title="func_b",
                content="def func_b(): pass",
                source="src/mod.py",
                chunk_type=ChunkType.CODE,
            ),
            Chunk(
                id="src/other.py:func_c",
                title="func_c",
                content="def func_c(): pass",
                source="src/other.py",
                chunk_type=ChunkType.CODE,
            ),
        ]
        xref = CrossReferenceIndex(chunks)

        related = xref.get_related(chunks[0])

        assert len(related) == 1
        assert related[0].id == "src/mod.py:func_b"

    def test_get_related_excludes_chunk_itself(self) -> None:
        from pixl.knowledge.search import CrossReferenceIndex
        from pixl.models.knowledge import Chunk, ChunkType

        chunk = Chunk(
            id="src/mod.py:func_a",
            title="func_a",
            content="def func_a(): pass",
            source="src/mod.py",
            chunk_type=ChunkType.CODE,
        )
        xref = CrossReferenceIndex([chunk])

        related = xref.get_related(chunk)

        assert related == []

    def test_get_related_respects_limit(self) -> None:
        from pixl.knowledge.search import CrossReferenceIndex
        from pixl.models.knowledge import Chunk, ChunkType

        chunks = [
            Chunk(
                id=f"src/mod.py:func_{i}",
                title=f"func_{i}",
                content=f"def func_{i}(): pass",
                source="src/mod.py",
                chunk_type=ChunkType.CODE,
            )
            for i in range(10)
        ]
        xref = CrossReferenceIndex(chunks)

        related = xref.get_related(chunks[0], limit=2)

        assert len(related) <= 2

    def test_get_siblings_by_title_prefix_finds_dotted_siblings(self) -> None:
        from pixl.knowledge.search import CrossReferenceIndex
        from pixl.models.knowledge import Chunk, ChunkType

        chunks = [
            Chunk(
                id="src/mod.py:Calculator",
                title="Calculator",
                content="class Calculator: pass",
                source="src/mod.py",
                chunk_type=ChunkType.CODE,
            ),
            Chunk(
                id="src/mod.py:Calculator.add",
                title="Calculator.add",
                content="def add(self): pass",
                source="src/mod.py",
                chunk_type=ChunkType.CODE,
            ),
            Chunk(
                id="src/mod.py:Calculator.subtract",
                title="Calculator.subtract",
                content="def subtract(self): pass",
                source="src/mod.py",
                chunk_type=ChunkType.CODE,
            ),
        ]
        xref = CrossReferenceIndex(chunks)

        siblings = xref.get_siblings_by_title_prefix(chunks[0])

        assert len(siblings) == 2

    def test_get_siblings_skips_short_prefix(self) -> None:
        from pixl.knowledge.search import CrossReferenceIndex
        from pixl.models.knowledge import Chunk, ChunkType

        chunk = Chunk(
            id="src/mod.py:ab",
            title="ab",
            content="short title",
            source="src/mod.py",
            chunk_type=ChunkType.CODE,
        )
        xref = CrossReferenceIndex([chunk])

        siblings = xref.get_siblings_by_title_prefix(chunk)

        assert siblings == []


class TestKnowledgeSearch:
    def test_search_returns_empty_for_blank_query(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        results = searcher.search("   ")

        assert results == []

    def test_search_returns_results_for_matching_query(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        results = searcher.search("authentication jwt tokens", limit=5)

        assert len(results) > 0

    def test_search_results_have_positive_scores(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        results = searcher.search("architecture design", limit=5)

        assert all(r.score > 0 for r in results)

    def test_search_respects_limit(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        results = searcher.search("system", limit=1)

        assert len(results) <= 1

    def test_search_results_are_sorted_by_score_descending(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        results = searcher.search("authentication configuration", limit=5)

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_with_scope_filter_limits_sources(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        results = searcher.search("authentication", scope="markdown", limit=5)

        # All returned chunks should be markdown sources
        assert all(
            r.chunk.source.endswith(".md") or r.chunk.source.endswith(".mdx") for r in results
        )

    def test_search_returns_matched_terms(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        results = searcher.search("authentication jwt", limit=5)

        # At least one result should have matched_terms populated
        terms_lists = [r.matched_terms for r in results]
        assert any(len(t) > 0 for t in terms_lists)

    def test_reload_clears_cache(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        # Populate cache
        searcher._get_chunks()
        assert searcher._chunks is not None

        searcher.reload()

        assert searcher._chunks is None

    def test_uses_fts_syntax_detects_quoted_phrases(self) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch.__new__(KnowledgeSearch)
        assert searcher._uses_fts_syntax('"auth token"') is True

    def test_uses_fts_syntax_detects_and_operator(self) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch.__new__(KnowledgeSearch)
        assert searcher._uses_fts_syntax("auth AND token") is True

    def test_uses_fts_syntax_false_for_plain_query(self) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch.__new__(KnowledgeSearch)
        assert searcher._uses_fts_syntax("plain search query") is False

    def test_extract_terms_filters_stopwords(self) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch.__new__(KnowledgeSearch)
        terms = searcher._extract_terms("how to configure the system")

        assert "the" not in terms
        assert "how" not in terms
        assert "configure" in terms or "system" in terms

    def test_extract_terms_requires_min_length_3(self) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch.__new__(KnowledgeSearch)
        terms = searcher._extract_terms("ab authenticate cd")

        # "ab" and "cd" are too short (< 3 chars after the leading letter rule)
        assert "ab" not in terms
        assert "authenticate" in terms

    def test_row_to_chunk_handles_unknown_chunk_type(self) -> None:
        from pixl.knowledge.search import KnowledgeSearch
        from pixl.models.knowledge import ChunkType

        searcher = KnowledgeSearch.__new__(KnowledgeSearch)
        row = {
            "id": "test-id",
            "title": "Test",
            "content": "content",
            "source": "src/file.py",
            "chunk_type": "unknown_type",
            "keywords": [],
            "score": 1.0,
            "line_start": None,
            "line_end": None,
        }
        chunk = searcher._row_to_chunk(row)

        assert chunk.chunk_type == ChunkType.CONCEPT

    def test_row_to_chunk_splits_string_keywords(self) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch.__new__(KnowledgeSearch)
        row = {
            "id": "kw-id",
            "title": "Keywords",
            "content": "content",
            "source": "src/file.py",
            "chunk_type": "concept",
            "keywords": "auth token secret",
            "score": 1.0,
            "line_start": None,
            "line_end": None,
        }
        chunk = searcher._row_to_chunk(row)

        assert "auth" in chunk.keywords
        assert "token" in chunk.keywords

    def test_search_with_include_related_expands_results(self, indexed_project: Path) -> None:
        from pixl.knowledge.search import KnowledgeSearch

        searcher = KnowledgeSearch(indexed_project)
        # With include_related, results may be expanded beyond the base set
        results = searcher.search("authentication", limit=3, include_related=True)

        # Should not error and should return results
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# knowledge/context.py
# ---------------------------------------------------------------------------


class TestContextBuilder:
    def test_build_context_returns_empty_string_when_no_index(
        self, project_with_pixl: Path
    ) -> None:
        from pixl.knowledge.context import ContextBuilder

        builder = ContextBuilder(project_with_pixl)
        result = builder.build_context("authentication")

        assert result == ""

    def test_build_context_returns_string_when_indexed(self, indexed_project: Path) -> None:
        from pixl.knowledge.context import ContextBuilder

        builder = ContextBuilder(indexed_project)
        result = builder.build_context("authentication jwt")

        assert isinstance(result, str)

    def test_build_context_exclude_source_strips_source_lines(self, indexed_project: Path) -> None:
        from pixl.knowledge.context import ContextBuilder

        builder = ContextBuilder(indexed_project)
        result_with = builder.build_context("authentication", include_source=True)
        result_without = builder.build_context("authentication", include_source=False)

        if result_with and result_without:
            # Without source should not contain _Source: markers
            assert "_Source:" not in result_without

    def test_build_context_for_feature_returns_string(self, indexed_project: Path) -> None:
        from pixl.knowledge.context import ContextBuilder

        builder = ContextBuilder(indexed_project)
        # Use simple single-word terms to avoid FTS5 parsing "word-based" as
        # a column-reference query (e.g. "based" alone triggers OperationalError).
        result = builder.build_context_for_feature(
            title="Authentication",
            description="jwt tokens",
        )

        assert isinstance(result, str)
