"""Tests for storage/db/artifacts.py, storage/db/chain_plans.py, and storage/db/projections.py.

Uses a real PixlDB backed by a tmp-dir SQLite so every test is isolated.
No mocks — testing real SQL against the real schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pixl.storage.db.chain_plans import ChainPlanDB
from pixl.storage.db.connection import PixlDB
from pixl.storage.db.projections import ProjectionStore

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path: Path) -> PixlDB:
    """Fresh PixlDB for each test, fully initialized with the current schema."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    pixl_db = PixlDB(tmp_path, pixl_dir=pixl_dir)
    pixl_db.initialize()
    return pixl_db


# ---------------------------------------------------------------------------
# Hierarchy helpers — seed the roadmap → epic → feature chain
# ---------------------------------------------------------------------------


def _seed_roadmap(db: PixlDB, roadmap_id: str = "roadmap-001", title: str = "Test Roadmap") -> str:
    db.conn.execute(
        "INSERT OR IGNORE INTO roadmaps (id, title, original_prompt) VALUES (?, ?, '')",
        (roadmap_id, title),
    )
    db.conn.commit()
    return roadmap_id


def _seed_epic(
    db: PixlDB,
    epic_id: str = "epic-001",
    roadmap_id: str | None = None,
    title: str = "Test Epic",
) -> str:
    if roadmap_id:
        _seed_roadmap(db, roadmap_id)
    db.conn.execute(
        "INSERT OR IGNORE INTO epics (id, roadmap_id, title, original_prompt) VALUES (?, ?, ?, '')",
        (epic_id, roadmap_id, title),
    )
    db.conn.commit()
    return epic_id


def _seed_feature(
    db: PixlDB,
    feature_id: str = "feat-001",
    epic_id: str | None = None,
    title: str = "Test Feature",
) -> str:
    db.conn.execute(
        "INSERT OR IGNORE INTO features (id, epic_id, title) VALUES (?, ?, ?)",
        (feature_id, epic_id, title),
    )
    db.conn.commit()
    return feature_id


def _seed_chain(
    db: PixlDB,
    chain_id: str = "chain-001",
    epic_id: str = "epic-001",
) -> str:
    """Seed an execution_chain row (requires epic_id to exist first)."""
    db.conn.execute(
        """INSERT OR IGNORE INTO execution_chains
           (id, epic_id, status, mode, max_parallel,
            failure_policy, stop_on_failure,
            validation_summary_json)
           VALUES (?, ?, 'plan_draft', 'plan_only',
                   1, 'branch_aware', 0, '{}')""",
        (chain_id, epic_id),
    )
    db.conn.commit()
    return chain_id


def _seed_chain_node(
    db: PixlDB,
    chain_id: str,
    node_id: str,
    feature_id: str | None = None,
    feature_ref: str | None = None,
    wave: int = 0,
) -> None:
    db.conn.execute(
        """INSERT OR IGNORE INTO execution_chain_nodes
           (chain_id, node_id, feature_id, feature_ref, wave, parallel_group, status, metadata_json)
           VALUES (?, ?, ?, ?, ?, 0, 'pending', '{}')""",
        (chain_id, node_id, feature_id, feature_ref or node_id, wave),
    )
    db.conn.commit()


def _seed_chain_edge(db: PixlDB, chain_id: str, from_node: str, to_node: str) -> None:
    db.conn.execute(
        """INSERT OR IGNORE INTO execution_chain_edges
           (chain_id, from_node_id, to_node_id)
           VALUES (?, ?, ?)""",
        (chain_id, from_node, to_node),
    )
    db.conn.commit()


def _seed_session(db: PixlDB, session_id: str) -> str:
    """Insert a minimal workflow_sessions row to satisfy the FK on artifacts.session_id."""
    db.conn.execute(
        "INSERT OR IGNORE INTO workflow_sessions (id, snapshot_hash) VALUES (?, ?)",
        (session_id, "hash-" + session_id),
    )
    db.conn.commit()
    return session_id


# ---------------------------------------------------------------------------
# Pre-seeded sessions for artifact tests
# ---------------------------------------------------------------------------
# Artifact.session_id references workflow_sessions(id) ON DELETE SET NULL.
# All tests that call db.artifacts.put() must ensure the session rows exist first.
# The simplest approach is to seed a set of session IDs before each test class.

_SEEDED_SESSIONS = [f"sess-{i:03d}" for i in range(1, 80)]


@pytest.fixture(autouse=False)
def seeded_sessions(db: PixlDB) -> None:
    """Pre-seed workflow_sessions rows for artifact FK satisfaction."""
    for sid in _SEEDED_SESSIONS:
        _seed_session(db, sid)


# ===========================================================================
# ArtifactDB tests
# ===========================================================================


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactPut:
    def test_put_creates_artifact_and_returns_dict(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-001",
            logical_path="docs/readme.md",
            content="Hello World",
            artifact_type="plan",
            task_id="task-001",
        )

        assert art["id"].startswith("art-")
        assert art["path"] == "docs/readme.md"
        assert art["session_id"] == "sess-001"
        assert art["content"] == "Hello World"
        assert art["type"] == "plan"

    def test_put_normalizes_sessions_prefix_in_path(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-002",
            logical_path="sessions/sess-002/artifacts/output.json",
            content="{}",
        )
        assert art["path"] == "output.json"

    def test_put_strips_artifacts_prefix(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-003",
            logical_path="artifacts/plan.md",
            content="plan content",
        )
        assert art["path"] == "plan.md"

    def test_put_with_tags_stores_and_deserializes_list(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-004",
            logical_path="tagged.md",
            content="content",
            tags=["alpha", "beta"],
        )
        assert art["tags"] == ["alpha", "beta"]

    def test_put_with_extra_stores_and_deserializes_dict(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-005",
            logical_path="meta.md",
            content="content",
            extra={"key": "value"},
        )
        assert art["extra"] == {"key": "value"}

    def test_put_defaults_version_to_1_0_0(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-006",
            logical_path="versioned.md",
            content="v1",
        )
        assert art["version"] == "1.0.0"

    def test_put_accepts_explicit_version(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-007",
            logical_path="explicit.md",
            content="v2",
            version="2.3.4",
        )
        assert art["version"] == "2.3.4"

    def test_put_raises_on_invalid_version(self, db: PixlDB) -> None:
        with pytest.raises(ValueError, match="Invalid version"):
            db.artifacts.put(
                session_id="sess-008",
                logical_path="bad.md",
                content="x",
                version="not-semver",
            )

    def test_put_raises_on_path_traversal(self, db: PixlDB) -> None:
        with pytest.raises(ValueError, match="traversal"):
            db.artifacts.put(
                session_id="sess-009",
                logical_path="../etc/passwd",
                content="hack",
            )

    def test_put_raises_on_empty_path(self, db: PixlDB) -> None:
        with pytest.raises(ValueError):
            db.artifacts.put(
                session_id="sess-010",
                logical_path="   ",
                content="empty",
            )


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactGet:
    def test_get_returns_artifact_by_id(self, db: PixlDB) -> None:
        art = db.artifacts.put(session_id="sess-011", logical_path="get.md", content="get me")
        fetched = db.artifacts.get(art["id"])
        assert fetched is not None
        assert fetched["id"] == art["id"]
        assert fetched["content"] == "get me"

    def test_get_returns_none_for_missing_id(self, db: PixlDB) -> None:
        assert db.artifacts.get("art-nonexistent") is None

    def test_get_by_session_path_returns_artifact(self, db: PixlDB) -> None:
        db.artifacts.put(session_id="sess-012", logical_path="notes.md", content="notes")
        fetched = db.artifacts.get_by_session_path("sess-012", "notes.md")
        assert fetched is not None
        assert fetched["content"] == "notes"

    def test_get_by_session_path_returns_none_for_missing(self, db: PixlDB) -> None:
        result = db.artifacts.get_by_session_path("sess-013", "missing.md")
        assert result is None

    def test_get_content_returns_content_string(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-014", logical_path="content.md", content="just content"
        )
        content = db.artifacts.get_content(art["id"])
        assert content == "just content"

    def test_get_content_returns_none_for_missing(self, db: PixlDB) -> None:
        assert db.artifacts.get_content("art-missing") is None

    def test_materialize_returns_content_by_session_path(self, db: PixlDB) -> None:
        db.artifacts.put(session_id="sess-015", logical_path="mat.md", content="materialized")
        result = db.artifacts.materialize(session_id="sess-015", logical_path="mat.md")
        assert result == "materialized"


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactList:
    def test_list_by_session_returns_all_for_session(self, db: PixlDB) -> None:
        db.artifacts.put(session_id="sess-020", logical_path="a.md", content="a")
        db.artifacts.put(session_id="sess-020", logical_path="b.md", content="b")
        db.artifacts.put(session_id="sess-021", logical_path="c.md", content="c")

        result = db.artifacts.list_by_session("sess-020")
        paths = [r["path"] for r in result]
        assert "a.md" in paths
        assert "b.md" in paths
        assert "c.md" not in paths

    def test_list_page_respects_limit_and_offset(self, db: PixlDB) -> None:
        for i in range(5):
            db.artifacts.put(
                session_id="sess-022", logical_path=f"file{i}.md", content=f"content{i}"
            )
        page1 = db.artifacts.list_page(session_id="sess-022", limit=3, offset=0)
        page2 = db.artifacts.list_page(session_id="sess-022", limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 2

    def test_list_page_all_returns_all_artifacts(self, db: PixlDB) -> None:
        db.artifacts.put(session_id="sess-023", logical_path="x.md", content="x")
        db.artifacts.put(session_id="sess-024", logical_path="y.md", content="y")
        result = db.artifacts.list_page_all(limit=100)
        assert len(result) >= 2

    def test_list_by_type_filters_correctly(self, db: PixlDB) -> None:
        db.artifacts.put(
            session_id="sess-025", logical_path="plan.md", content="p", artifact_type="plan"
        )
        db.artifacts.put(
            session_id="sess-025", logical_path="code.py", content="c", artifact_type="code"
        )
        result = db.artifacts.list_by_type("plan")
        assert all(r["type"] == "plan" for r in result)

    def test_list_by_task_returns_task_artifacts(self, db: PixlDB) -> None:
        db.artifacts.put(
            session_id="sess-026",
            logical_path="task-output.md",
            content="output",
            task_id="task-xyz",
        )
        result = db.artifacts.list_by_task("task-xyz")
        assert len(result) >= 1
        assert all(r["task_id"] == "task-xyz" for r in result)

    def test_list_by_feature_returns_feature_artifacts(self, db: PixlDB) -> None:
        _seed_feature(db, "feat-list-001")
        db.artifacts.put(
            session_id="sess-027",
            logical_path="feat-output.md",
            content="feat content",
            feature_id="feat-list-001",
        )
        result = db.artifacts.list_by_feature("feat-list-001")
        assert len(result) >= 1
        assert all(r["feature_id"] == "feat-list-001" for r in result)

    def test_list_by_epic_returns_epic_artifacts(self, db: PixlDB) -> None:
        _seed_epic(db, epic_id="epic-list-001")
        db.artifacts.put(
            session_id="sess-028",
            logical_path="epic-output.md",
            content="epic content",
            epic_id="epic-list-001",
        )
        result = db.artifacts.list_by_epic("epic-list-001")
        assert len(result) >= 1
        assert all(r["epic_id"] == "epic-list-001" for r in result)


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactUpdate:
    def test_update_changes_specified_fields(self, db: PixlDB) -> None:
        art = db.artifacts.put(session_id="sess-030", logical_path="update.md", content="before")
        updated = db.artifacts.update(art["id"], content="after")
        assert updated is True
        fetched = db.artifacts.get(art["id"])
        assert fetched is not None
        assert fetched["content"] == "after"

    def test_update_returns_false_for_missing_id(self, db: PixlDB) -> None:
        result = db.artifacts.update("art-no-exist", content="x")
        assert result is False

    def test_update_tags_deserializes_correctly(self, db: PixlDB) -> None:
        art = db.artifacts.put(session_id="sess-031", logical_path="tags.md", content="c")
        db.artifacts.update(art["id"], tags=["new-tag"])
        fetched = db.artifacts.get(art["id"])
        assert fetched is not None
        assert "new-tag" in fetched["tags"]


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactDelete:
    def test_delete_removes_artifact(self, db: PixlDB) -> None:
        art = db.artifacts.put(session_id="sess-040", logical_path="todel.md", content="bye")
        result = db.artifacts.delete(art["id"])
        assert result is True
        assert db.artifacts.get(art["id"]) is None

    def test_delete_returns_false_for_missing_id(self, db: PixlDB) -> None:
        assert db.artifacts.delete("art-ghost") is False


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactSearch:
    def test_search_finds_artifact_by_content_keyword(self, db: PixlDB) -> None:
        db.artifacts.put(
            session_id="sess-050",
            logical_path="searchable.md",
            content="uniquekeyword for testing full text search",
            name="searchable",
        )
        results = db.artifacts.search(query="uniquekeyword", limit=5)
        assert len(results) >= 1
        assert any("uniquekeyword" in (r.get("content") or "") for r in results)

    def test_search_empty_query_returns_empty_list(self, db: PixlDB) -> None:
        results = db.artifacts.search(query="   ")
        assert results == []

    def test_search_session_scoped(self, db: PixlDB) -> None:
        db.artifacts.put(
            session_id="sess-051",
            logical_path="scoped.md",
            content="scopedcontentxyz session specific artifact",
            name="scoped",
        )
        results = db.artifacts.search_session(session_id="sess-051", query="scopedcontentxyz")
        assert len(results) >= 1

    def test_find_by_hash_returns_matching_artifact(self, db: PixlDB) -> None:
        import hashlib

        content = "hashable content"
        art = db.artifacts.put(session_id="sess-052", logical_path="hash.md", content=content)
        expected_hash = hashlib.sha256(content.encode()).hexdigest()
        found = db.artifacts.find_by_hash(expected_hash)
        assert found is not None
        assert found["id"] == art["id"]


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactVersioning:
    def test_create_version_creates_new_version_artifact(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-060", logical_path="versioned.md", content="v1 content"
        )
        v2 = db.artifacts.create_version(
            original_artifact_id=art["id"],
            task_id="task-v2",
            session_id="sess-060",
            content="v2 content",
            change_description="increment",
        )
        assert v2["path"] == "versioned.md"
        assert v2["content"] == "v2 content"
        assert v2["previous_version_id"] == art["id"]

    def test_get_versions_returns_all_versions(self, db: PixlDB) -> None:
        art = db.artifacts.put(session_id="sess-061", logical_path="multi.md", content="v1")
        db.artifacts.create_version(
            original_artifact_id=art["id"],
            task_id="t",
            session_id="sess-061",
            content="v2",
        )
        versions = db.artifacts.get_versions(art["id"])
        assert len(versions) >= 2

    def test_get_latest_version_returns_highest_version(self, db: PixlDB) -> None:
        art = db.artifacts.put(session_id="sess-062", logical_path="latest.md", content="v1")
        db.artifacts.create_version(
            original_artifact_id=art["id"],
            task_id="t",
            session_id="sess-062",
            content="v2",
        )
        latest = db.artifacts.get_latest_version(art["id"])
        assert latest is not None
        # Should be the highest version (not necessarily the original)
        assert latest["path"] == "latest.md"

    def test_create_version_raises_for_missing_original(self, db: PixlDB) -> None:
        with pytest.raises(ValueError, match="not found"):
            db.artifacts.create_version(
                original_artifact_id="art-ghost",
                task_id="t",
                session_id="sess-063",
            )

    def test_compare_versions_returns_diff_info(self, db: PixlDB) -> None:
        art = db.artifacts.put(
            session_id="sess-064",
            logical_path="compare.md",
            content="line1\nline2",
            version="1.0.0",
        )
        db.artifacts.put(
            session_id="sess-064",
            logical_path="compare.md",
            content="line1\nline2\nline3",
            version="1.0.1",
        )
        result = db.artifacts.compare_versions(art["id"], "1.0.0", "1.0.1")
        assert result is not None
        assert result["content_changed"] is True
        assert result["line_count_diff"] == 1

    def test_list_versions_by_path_returns_ordered_versions(self, db: PixlDB) -> None:
        db.artifacts.put(
            session_id="sess-065", logical_path="ordered.md", content="v1", version="1.0.0"
        )
        db.artifacts.put(
            session_id="sess-065", logical_path="ordered.md", content="v2", version="2.0.0"
        )
        versions = db.artifacts.list_versions_by_path("ordered.md", session_id="sess-065")
        assert len(versions) == 2
        # Latest first
        assert versions[0]["version"] == "2.0.0"

    def test_list_versions_by_path_v2_alias_works(self, db: PixlDB) -> None:
        db.artifacts.put(session_id="sess-066", logical_path="alias.md", content="v1")
        result = db.artifacts.list_versions_by_path_v2("alias.md")
        assert isinstance(result, list)


@pytest.mark.usefixtures("seeded_sessions")
class TestArtifactCreate:
    """Tests for the backward-compatible create() API."""

    def test_create_delegates_to_put(self, db: PixlDB) -> None:
        art = db.artifacts.create(
            name="legacy-artifact",
            artifact_type="plan",
            task_id="task-legacy",
            session_id="sess-070",
            content="legacy content",
        )
        assert art["name"] == "legacy-artifact"
        assert art["content"] == "legacy content"
        assert art["type"] == "plan"


# ===========================================================================
# ChainPlanDB tests
# ===========================================================================


@pytest.fixture()
def chain_db(db: PixlDB) -> ChainPlanDB:
    return ChainPlanDB(db)


@pytest.fixture()
def simple_chain(db: PixlDB) -> dict[str, Any]:
    """Seed a chain with 2 nodes (wave 0 and wave 1) and one edge."""
    epic_id = _seed_epic(db, "epic-chain-001")
    chain_id = _seed_chain(db, "chain-100", epic_id)
    _seed_chain_node(db, chain_id, "node-A", wave=0, feature_ref="ref-A")
    _seed_chain_node(db, chain_id, "node-B", wave=1, feature_ref="ref-B")
    _seed_chain_edge(db, chain_id, "node-A", "node-B")
    return {"chain_id": chain_id, "epic_id": epic_id}


class TestChainPlanGet:
    def test_get_chain_returns_dict_for_existing_chain(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        result = chain_db.get_chain(simple_chain["chain_id"])
        assert result is not None
        assert result["id"] == simple_chain["chain_id"]
        assert result["epic_id"] == simple_chain["epic_id"]

    def test_get_chain_returns_none_for_missing(self, chain_db: ChainPlanDB) -> None:
        assert chain_db.get_chain("chain-ghost") is None

    def test_get_chain_by_epic_returns_chain(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        result = chain_db.get_chain_by_epic(simple_chain["epic_id"])
        assert result is not None
        assert result["id"] == simple_chain["chain_id"]

    def test_get_chain_by_epic_returns_none_for_missing_epic(self, chain_db: ChainPlanDB) -> None:
        assert chain_db.get_chain_by_epic("epic-ghost") is None

    def test_get_plan_returns_nodes_and_edges(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        plan = chain_db.get_plan(simple_chain["chain_id"])
        assert plan is not None
        assert len(plan["nodes"]) == 2
        assert len(plan["edges"]) == 1

    def test_get_plan_returns_none_for_missing_chain(self, chain_db: ChainPlanDB) -> None:
        assert chain_db.get_plan("chain-ghost") is None

    def test_get_chain_detail_includes_waves(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        detail = chain_db.get_chain_detail(simple_chain["chain_id"])
        assert detail is not None
        assert len(detail["waves"]) >= 1
        assert detail["chain_id"] == simple_chain["chain_id"]


class TestChainPlanList:
    def test_list_chains_returns_all_chains(
        self, db: PixlDB, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        result = chain_db.list_chains()
        chain_ids = [c["id"] for c in result]
        assert simple_chain["chain_id"] in chain_ids

    def test_list_chains_includes_node_counts(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        result = chain_db.list_chains()
        chain = next(c for c in result if c["id"] == simple_chain["chain_id"])
        assert "node_counts" in chain
        assert chain["node_counts"]["total"] == 2
        assert chain["node_counts"]["pending"] == 2


class TestChainPlanNodes:
    def test_get_nodes_returns_nodes_for_chain(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        nodes = chain_db.get_nodes(simple_chain["chain_id"])
        assert len(nodes) == 2

    def test_get_nodes_excludes_execution_columns_by_default(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        nodes = chain_db.get_nodes(simple_chain["chain_id"])
        # status is not in the default non-execution column list
        for node in nodes:
            assert "status" not in node

    def test_get_execution_nodes_includes_status(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        nodes = chain_db.get_execution_nodes(simple_chain["chain_id"])
        assert len(nodes) == 2
        for node in nodes:
            assert "status" in node

    def test_get_edges_returns_edges_for_chain(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        edges = chain_db.get_edges(simple_chain["chain_id"])
        assert len(edges) == 1
        assert edges[0]["from"] == "node-A"
        assert edges[0]["to"] == "node-B"


class TestChainPlanStatus:
    def test_set_chain_status_updates_status(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.set_chain_status(simple_chain["chain_id"], "plan_ready")
        chain = chain_db.get_chain(simple_chain["chain_id"])
        assert chain is not None
        assert chain["status"] == "plan_ready"

    def test_start_chain_requires_plan_ready(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        # chain starts as plan_draft, start should fail
        with pytest.raises(ValueError, match="plan_ready"):
            chain_db.start_chain(simple_chain["chain_id"])

    def test_start_chain_succeeds_when_plan_ready(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.set_chain_status(simple_chain["chain_id"], "plan_ready")
        plan = chain_db.start_chain(simple_chain["chain_id"])
        assert plan["status"] == "running"

    def test_pause_chain_requires_running(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        with pytest.raises(ValueError, match="running"):
            chain_db.pause_chain(simple_chain["chain_id"])

    def test_pause_and_resume_cycle(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.set_chain_status(simple_chain["chain_id"], "plan_ready")
        chain_db.start_chain(simple_chain["chain_id"])
        chain_db.pause_chain(simple_chain["chain_id"])
        chain = chain_db.get_chain(simple_chain["chain_id"])
        assert chain is not None
        assert chain["status"] == "paused"

        chain_db.resume_chain(simple_chain["chain_id"])
        chain = chain_db.get_chain(simple_chain["chain_id"])
        assert chain is not None
        assert chain["status"] == "running"

    def test_cancel_chain_marks_as_cancelled(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain = chain_db.cancel_chain(simple_chain["chain_id"])
        assert chain["status"] == "cancelled"

    def test_cancel_terminal_chain_raises(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.cancel_chain(simple_chain["chain_id"])
        with pytest.raises(ValueError, match="terminal"):
            chain_db.cancel_chain(simple_chain["chain_id"])


class TestChainPlanNodeLifecycle:
    def test_try_claim_node_transitions_pending_to_running(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        claimed = chain_db.try_claim_node_for_execution(
            simple_chain["chain_id"], "node-A", session_id="sess-exec-001"
        )
        assert claimed is True
        nodes = chain_db.get_execution_nodes(simple_chain["chain_id"])
        node_a = next(n for n in nodes if n["node_id"] == "node-A")
        assert node_a["status"] == "running"

    def test_try_claim_already_running_node_returns_false(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.try_claim_node_for_execution(
            simple_chain["chain_id"], "node-A", session_id="sess-exec-002"
        )
        # Second claim should fail (already running)
        claimed = chain_db.try_claim_node_for_execution(
            simple_chain["chain_id"], "node-A", session_id="sess-exec-003"
        )
        assert claimed is False

    def test_mark_node_completed_sets_status(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.try_claim_node_for_execution(
            simple_chain["chain_id"], "node-A", session_id="sess-exec-004"
        )
        chain_db.mark_node_completed(simple_chain["chain_id"], "node-A")
        nodes = chain_db.get_execution_nodes(simple_chain["chain_id"])
        node_a = next(n for n in nodes if n["node_id"] == "node-A")
        assert node_a["status"] == "completed"

    def test_mark_node_failed_sets_error(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.mark_node_failed(simple_chain["chain_id"], "node-A", error="something went wrong")
        nodes = chain_db.get_execution_nodes(simple_chain["chain_id"])
        node_a = next(n for n in nodes if n["node_id"] == "node-A")
        assert node_a["status"] == "failed"
        assert node_a["error"] == "something went wrong"

    def test_set_node_error_without_status_change(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.set_node_error(simple_chain["chain_id"], "node-A", error="blocked by dep")
        nodes = chain_db.get_execution_nodes(simple_chain["chain_id"])
        node_a = next(n for n in nodes if n["node_id"] == "node-A")
        # Status unchanged — still pending
        assert node_a["status"] == "pending"
        assert node_a["error"] == "blocked by dep"

    def test_mark_nodes_blocked_transitions_pending_nodes(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.mark_nodes_blocked(
            simple_chain["chain_id"],
            ["node-A", "node-B"],
            reason="cascade block",
        )
        nodes = chain_db.get_execution_nodes(simple_chain["chain_id"])
        for node in nodes:
            assert node["status"] == "blocked"

    def test_mark_nodes_cancelled_transitions_pending_nodes(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.mark_nodes_cancelled(simple_chain["chain_id"], ["node-A"], reason="abort")
        nodes = chain_db.get_execution_nodes(simple_chain["chain_id"])
        node_a = next(n for n in nodes if n["node_id"] == "node-A")
        assert node_a["status"] == "cancelled"


class TestChainPlanUpdateNodeMetadata:
    def test_update_node_metadata_merges_keys(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        meta = chain_db.update_node_metadata(
            simple_chain["chain_id"], "node-A", updates={"foo": "bar"}
        )
        assert meta["foo"] == "bar"

    def test_update_node_metadata_idempotent_on_repeated_calls(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.update_node_metadata(simple_chain["chain_id"], "node-A", updates={"key": "v1"})
        meta = chain_db.update_node_metadata(
            simple_chain["chain_id"], "node-A", updates={"key": "v2"}
        )
        assert meta["key"] == "v2"


class TestChainPlanValidation:
    def test_validate_chain_marks_dag_valid_for_valid_graph(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        result = chain_db.validate_chain(simple_chain["chain_id"])
        assert result["validation_summary"]["dag_valid"] is True

    def test_validate_chain_raises_for_missing_chain(self, chain_db: ChainPlanDB) -> None:
        with pytest.raises(ValueError, match="not found"):
            chain_db.validate_chain("chain-ghost")


class TestChainPlanPatch:
    def test_patch_plan_updates_max_parallel(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.patch_plan(simple_chain["chain_id"], max_parallel=3)
        chain = chain_db.get_chain(simple_chain["chain_id"])
        assert chain is not None
        assert chain["max_parallel"] == 3

    def test_patch_plan_updates_node_wave(self, db: PixlDB, chain_db: ChainPlanDB) -> None:
        epic_id = _seed_epic(db, "epic-patch-001")
        chain_id = _seed_chain(db, "chain-patch-001", epic_id)
        _seed_chain_node(db, chain_id, "pnode-A", wave=0, feature_ref="pref-A")
        _seed_chain_node(db, chain_id, "pnode-B", wave=1, feature_ref="pref-B")
        # No edge between A and B for simpler wave update test
        chain_db.patch_plan(
            chain_id,
            node_updates=[{"node_id": "pnode-B", "wave": 2}],
        )
        nodes = chain_db.get_nodes(chain_id)
        node_b = next(n for n in nodes if n["node_id"] == "pnode-B")
        assert int(node_b["wave"]) == 2

    def test_patch_plan_raises_on_invalid_max_parallel(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        with pytest.raises(ValueError, match="max_parallel"):
            chain_db.patch_plan(simple_chain["chain_id"], max_parallel=0)

    def test_patch_plan_raises_on_invalid_risk_class(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        with pytest.raises(ValueError, match="risk_class"):
            chain_db.patch_plan(
                simple_chain["chain_id"],
                node_updates=[{"node_id": "node-A", "risk_class": "ultra-high"}],
            )


class TestChainPlanReset:
    def test_reset_chain_restores_plan_ready(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.set_chain_status(simple_chain["chain_id"], "failed")
        chain = chain_db.reset_chain(simple_chain["chain_id"])
        assert chain["status"] == "plan_ready"

    def test_reset_chain_raises_for_non_terminal_status(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        # Default status is plan_draft, not failed/cancelled
        with pytest.raises(ValueError, match="failed/cancelled"):
            chain_db.reset_chain(simple_chain["chain_id"])


class TestChainPlanConfigure:
    def test_configure_chain_execution_sets_max_parallel(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.configure_chain_execution(simple_chain["chain_id"], max_parallel=5)
        chain = chain_db.get_chain(simple_chain["chain_id"])
        assert chain is not None
        assert chain["max_parallel"] == 5

    def test_configure_chain_execution_sets_stop_on_failure(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        chain_db.configure_chain_execution(simple_chain["chain_id"], stop_on_failure=True)
        chain = chain_db.get_chain(simple_chain["chain_id"])
        assert chain is not None
        assert chain["stop_on_failure"] is True

    def test_configure_raises_on_zero_max_parallel(
        self, chain_db: ChainPlanDB, simple_chain: dict[str, Any]
    ) -> None:
        with pytest.raises(ValueError, match="max_parallel"):
            chain_db.configure_chain_execution(simple_chain["chain_id"], max_parallel=0)


# ===========================================================================
# ProjectionStore tests
# ===========================================================================


@pytest.fixture()
def proj(db: PixlDB) -> ProjectionStore:
    return ProjectionStore(db)


class TestProjectionFactoryHome:
    def test_factory_home_returns_expected_keys(self, proj: ProjectionStore) -> None:
        result = proj.factory_home()
        assert "live_runs" in result
        assert "pending_gates" in result
        assert "recovering" in result
        assert "recently_completed" in result
        assert "health" in result
        assert "autonomy" in result

    def test_factory_home_live_runs_is_list(self, proj: ProjectionStore) -> None:
        result = proj.factory_home()
        assert isinstance(result["live_runs"], list)

    def test_factory_home_health_has_success_rate(self, proj: ProjectionStore) -> None:
        result = proj.factory_home()
        assert "success_rate" in result["health"]
        assert isinstance(result["health"]["success_rate"], float)

    def test_factory_home_autonomy_has_total_outcomes(self, proj: ProjectionStore) -> None:
        result = proj.factory_home()
        assert "total_outcomes" in result["autonomy"]

    def test_factory_home_empty_db_returns_zero_live_runs(self, proj: ProjectionStore) -> None:
        result = proj.factory_home()
        assert result["live_runs"] == []


class TestProjectionRoadmapRollup:
    def test_roadmap_rollup_empty_returns_empty_list(self, proj: ProjectionStore) -> None:
        result = proj.roadmap_rollup()
        assert result == []

    def test_roadmap_rollup_returns_seeded_roadmap(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_roadmap(db, "roadmap-proj-001", "Proj Roadmap")
        result = proj.roadmap_rollup()
        assert len(result) >= 1
        ids = [r["id"] for r in result]
        assert "roadmap-proj-001" in ids

    def test_roadmap_rollup_filtered_by_id(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_roadmap(db, "roadmap-proj-002", "Filtered Roadmap")
        _seed_roadmap(db, "roadmap-proj-003", "Other Roadmap")
        result = proj.roadmap_rollup("roadmap-proj-002")
        assert len(result) == 1
        assert result[0]["id"] == "roadmap-proj-002"

    def test_roadmap_rollup_includes_progress_pct(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_roadmap(db, "roadmap-proj-004", "Progress Roadmap")
        result = proj.roadmap_rollup("roadmap-proj-004")
        assert len(result) == 1
        assert "progress_pct" in result[0]

    def test_roadmap_rollup_counts_epics(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_roadmap(db, "roadmap-proj-005")
        _seed_epic(db, "epic-proj-001", roadmap_id="roadmap-proj-005")
        _seed_epic(db, "epic-proj-002", roadmap_id="roadmap-proj-005")
        result = proj.roadmap_rollup("roadmap-proj-005")
        assert len(result) == 1
        assert result[0]["epic_count"] == 2

    def test_roadmap_rollup_includes_top_blockers_key(
        self, db: PixlDB, proj: ProjectionStore
    ) -> None:
        _seed_roadmap(db, "roadmap-proj-006")
        result = proj.roadmap_rollup("roadmap-proj-006")
        assert "top_blockers" in result[0]

    def test_roadmap_rollup_includes_confidence_key(
        self, db: PixlDB, proj: ProjectionStore
    ) -> None:
        _seed_roadmap(db, "roadmap-proj-007")
        result = proj.roadmap_rollup("roadmap-proj-007")
        assert "confidence" in result[0]
        assert result[0]["confidence"] == 1.0  # no incidents → full confidence


class TestProjectionEpicRollup:
    def test_epic_rollup_empty_returns_empty_list(self, proj: ProjectionStore) -> None:
        result = proj.epic_rollup()
        assert result == []

    def test_epic_rollup_returns_seeded_epic(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_epic(db, "epic-rollup-001", title="Rollup Epic")
        result = proj.epic_rollup()
        ids = [r["id"] for r in result]
        assert "epic-rollup-001" in ids

    def test_epic_rollup_filtered_by_id(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_epic(db, "epic-rollup-002")
        _seed_epic(db, "epic-rollup-003")
        result = proj.epic_rollup("epic-rollup-002")
        assert len(result) == 1
        assert result[0]["id"] == "epic-rollup-002"

    def test_epic_rollup_includes_features_by_status(
        self, db: PixlDB, proj: ProjectionStore
    ) -> None:
        _seed_epic(db, "epic-rollup-004")
        _seed_feature(db, "feat-rollup-001", epic_id="epic-rollup-004")
        result = proj.epic_rollup("epic-rollup-004")
        assert len(result) == 1
        assert "features_by_status" in result[0]

    def test_epic_rollup_counts_done_features(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_epic(db, "epic-rollup-005")
        _seed_feature(db, "feat-rollup-done-001", epic_id="epic-rollup-005")
        db.conn.execute(
            "UPDATE features SET status = 'done' WHERE id = ?",
            ("feat-rollup-done-001",),
        )
        db.conn.commit()
        result = proj.epic_rollup("epic-rollup-005")
        assert result[0]["features_by_status"]["done"] == 1

    def test_epic_rollup_includes_active_runs_key(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_epic(db, "epic-rollup-006")
        result = proj.epic_rollup("epic-rollup-006")
        assert "active_runs" in result[0]

    def test_epic_rollup_includes_blockers_key(self, db: PixlDB, proj: ProjectionStore) -> None:
        _seed_epic(db, "epic-rollup-007")
        result = proj.epic_rollup("epic-rollup-007")
        assert "blockers" in result[0]


class TestProjectionEpicExecutionPlan:
    def test_epic_execution_plan_returns_none_without_chain(
        self, db: PixlDB, proj: ProjectionStore
    ) -> None:
        _seed_epic(db, "epic-exec-001")
        result = proj.epic_execution_plan("epic-exec-001")
        assert result is None

    def test_epic_execution_plan_returns_chain_data(
        self, db: PixlDB, proj: ProjectionStore
    ) -> None:
        _seed_epic(db, "epic-exec-002")
        _seed_chain(db, "chain-exec-001", "epic-exec-002")
        _seed_chain_node(db, "chain-exec-001", "enode-A", wave=0, feature_ref="eref-A")
        result = proj.epic_execution_plan("epic-exec-002")
        assert result is not None
        assert "nodes" in result
        assert len(result["nodes"]) == 1
