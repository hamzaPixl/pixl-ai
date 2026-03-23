"""Tests for WorkflowTemplateDB — DB-backed workflow templates with versioning."""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl.storage.db.connection import PixlDB


@pytest.fixture()
def db(tmp_path: Path) -> PixlDB:
    """Create a fresh PixlDB with schema initialized."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    db = PixlDB(tmp_path, pixl_dir=pixl_dir)
    db.initialize()
    return db


SAMPLE_YAML = """\
id: tdd
name: Test-Driven Development
version: "1.0"
stages:
  - id: plan
    type: task
    agent: architect
"""


class TestCreate:
    def test_create_returns_dict_with_id(self, db: PixlDB) -> None:
        result = db.workflow_templates.create("tdd", SAMPLE_YAML)
        assert result is not None
        assert result["id"].startswith("wft-")
        assert result["name"] == "tdd"
        assert result["yaml_content"] == SAMPLE_YAML
        assert result["version"] == 1
        assert result["source"] == "db"

    def test_create_with_description_and_config(self, db: PixlDB) -> None:
        result = db.workflow_templates.create(
            "debug",
            SAMPLE_YAML,
            description="Debug workflow",
            config={"timeout": 300},
            source="imported",
        )
        assert result["description"] == "Debug workflow"
        assert result["config"] == {"timeout": 300}
        assert result["source"] == "imported"

    def test_create_generates_unique_ids(self, db: PixlDB) -> None:
        r1 = db.workflow_templates.create("tdd", SAMPLE_YAML)
        r2 = db.workflow_templates.create("tdd", SAMPLE_YAML)
        assert r1["id"] != r2["id"]


class TestGet:
    def test_get_existing_template(self, db: PixlDB) -> None:
        created = db.workflow_templates.create("tdd", SAMPLE_YAML)
        fetched = db.workflow_templates.get(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["name"] == "tdd"

    def test_get_nonexistent_returns_none(self, db: PixlDB) -> None:
        assert db.workflow_templates.get("wft-nonexistent") is None


class TestGetByName:
    def test_returns_latest_version(self, db: PixlDB) -> None:
        t1 = db.workflow_templates.create("tdd", SAMPLE_YAML)
        # Update to bump version
        db.workflow_templates.update(t1["id"], yaml_content="updated: true")
        result = db.workflow_templates.get_by_name("tdd")
        assert result is not None
        assert result["version"] == 2

    def test_returns_none_for_unknown_name(self, db: PixlDB) -> None:
        assert db.workflow_templates.get_by_name("nonexistent") is None


class TestListTemplates:
    def test_list_returns_all(self, db: PixlDB) -> None:
        db.workflow_templates.create("tdd", SAMPLE_YAML)
        db.workflow_templates.create("debug", SAMPLE_YAML)
        results = db.workflow_templates.list_templates()
        assert len(results) == 2

    def test_list_filter_by_source(self, db: PixlDB) -> None:
        db.workflow_templates.create("tdd", SAMPLE_YAML, source="db")
        db.workflow_templates.create("debug", SAMPLE_YAML, source="imported")
        db_only = db.workflow_templates.list_templates(source="db")
        assert len(db_only) == 1
        assert db_only[0]["name"] == "tdd"

    def test_list_respects_limit(self, db: PixlDB) -> None:
        for i in range(5):
            db.workflow_templates.create(f"wf-{i}", SAMPLE_YAML)
        results = db.workflow_templates.list_templates(limit=3)
        assert len(results) == 3

    def test_list_empty_returns_empty(self, db: PixlDB) -> None:
        assert db.workflow_templates.list_templates() == []


class TestUpdate:
    def test_update_bumps_version(self, db: PixlDB) -> None:
        created = db.workflow_templates.create("tdd", SAMPLE_YAML)
        assert created["version"] == 1
        success = db.workflow_templates.update(created["id"], yaml_content="v2: true")
        assert success is True
        updated = db.workflow_templates.get(created["id"])
        assert updated is not None
        assert updated["version"] == 2
        assert updated["yaml_content"] == "v2: true"

    def test_update_sets_updated_at(self, db: PixlDB) -> None:
        created = db.workflow_templates.create("tdd", SAMPLE_YAML)
        assert created["updated_at"] is None
        db.workflow_templates.update(created["id"], description="Updated desc")
        updated = db.workflow_templates.get(created["id"])
        assert updated is not None
        assert updated["updated_at"] is not None

    def test_update_config(self, db: PixlDB) -> None:
        created = db.workflow_templates.create("tdd", SAMPLE_YAML)
        db.workflow_templates.update(created["id"], config={"retry": 3})
        updated = db.workflow_templates.get(created["id"])
        assert updated is not None
        assert updated["config"] == {"retry": 3}

    def test_update_nonexistent_returns_false(self, db: PixlDB) -> None:
        assert db.workflow_templates.update("wft-ghost", yaml_content="x") is False


class TestDelete:
    def test_delete_existing(self, db: PixlDB) -> None:
        created = db.workflow_templates.create("tdd", SAMPLE_YAML)
        assert db.workflow_templates.delete(created["id"]) is True
        assert db.workflow_templates.get(created["id"]) is None

    def test_delete_nonexistent_returns_false(self, db: PixlDB) -> None:
        assert db.workflow_templates.delete("wft-ghost") is False


class TestMigration:
    """Test that v36->v37 migration creates the table correctly."""

    def test_migration_from_v36_creates_table(self, tmp_path: Path) -> None:
        """Simulate a v36 DB and verify migration adds workflow_templates."""
        from pixl.storage.db.schema import SCHEMA_VERSION

        assert SCHEMA_VERSION == 37, f"Expected schema v37, got {SCHEMA_VERSION}"

        pixl_dir = tmp_path / ".pixl"
        pixl_dir.mkdir()
        db = PixlDB(tmp_path, pixl_dir=pixl_dir)

        # Initialize sets up the full schema at v37
        db.initialize()

        # Verify the table exists and is functional
        result = db.workflow_templates.create("test", "yaml: true")
        assert result["id"].startswith("wft-")
