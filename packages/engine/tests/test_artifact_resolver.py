"""Tests for the extracted ArtifactResolver collaborator.

Validates that ArtifactResolver correctly resolves artifact paths,
builds handoff manifests, and checks required inputs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pixl.execution.artifact_resolver import ArtifactResolver


def _make_store() -> MagicMock:
    """Create a mock WorkflowSessionStore."""
    store = MagicMock()
    store._get_db = MagicMock()
    store.load_artifact = MagicMock(return_value=None)
    return store


def _make_resolver(
    session_id: str = "sess-1",
    artifacts_dir: Path | None = None,
    store: MagicMock | None = None,
    build_contract_variables: Any = None,
) -> ArtifactResolver:
    """Create an ArtifactResolver with sensible test defaults."""
    if artifacts_dir is None:
        artifacts_dir = Path("/tmp/test-artifacts")
    if store is None:
        store = _make_store()
    if build_contract_variables is None:
        build_contract_variables = lambda node_id: {}

    return ArtifactResolver(
        session_id=session_id,
        artifacts_dir=artifacts_dir,
        store=store,
        build_contract_variables=build_contract_variables,
    )


class TestResolveRequiredArtifactPath:
    def test_strips_artifacts_prefix(self) -> None:
        resolver = _make_resolver()

        result = resolver.resolve_required_artifact_path("artifacts/plan.md", {})

        assert result == "plan.md"

    def test_strips_leading_slash(self) -> None:
        resolver = _make_resolver()

        result = resolver.resolve_required_artifact_path("/plan.md", {})

        assert result == "plan.md"

    def test_normalizes_backslashes(self) -> None:
        resolver = _make_resolver()

        result = resolver.resolve_required_artifact_path("docs\\plan.md", {})

        assert result == "docs/plan.md"

    def test_strips_absolute_artifacts_dir(self) -> None:
        artifacts_dir = Path("/tmp/test-artifacts")
        resolver = _make_resolver(artifacts_dir=artifacts_dir)

        result = resolver.resolve_required_artifact_path(
            "/tmp/test-artifacts/plan.md", {}
        )

        assert result == "plan.md"

    def test_resolves_template_variables(self) -> None:
        resolver = _make_resolver()

        result = resolver.resolve_required_artifact_path(
            "{{feature_name}}-plan.md", {"feature_name": "auth"}
        )

        assert result == "auth-plan.md"


class TestLoadArtifactRowSafe:
    def test_returns_row_from_db(self) -> None:
        store = _make_store()
        db = MagicMock()
        db.artifacts.get_by_session_path = MagicMock(
            return_value={"path": "plan.md", "content_hash": "abc123"}
        )
        store._get_db.return_value = db
        resolver = _make_resolver(store=store)

        result = resolver.load_artifact_row_safe("plan.md")

        assert result is not None
        assert result["path"] == "plan.md"

    def test_returns_none_on_exception(self) -> None:
        store = _make_store()
        store._get_db.side_effect = Exception("DB error")
        resolver = _make_resolver(store=store)

        result = resolver.load_artifact_row_safe("plan.md")

        assert result is None


class TestBuildArtifactHandoffManifest:
    def test_empty_artifacts_returns_empty_list(self) -> None:
        resolver = _make_resolver()

        result = resolver.build_artifact_handoff_manifest("node-1", [])

        assert result == []

    def test_missing_artifact_marked_not_exists(self) -> None:
        store = _make_store()
        db = MagicMock()
        db.artifacts.get_by_session_path = MagicMock(return_value=None)
        store._get_db.return_value = db
        store.load_artifact.return_value = None

        resolver = _make_resolver(store=store)

        result = resolver.build_artifact_handoff_manifest("node-1", ["plan.md"])

        assert len(result) == 1
        assert result[0]["path"] == "plan.md"
        assert result[0]["exists"] is False
        assert result[0]["sha256"] is None

    def test_existing_db_artifact_marked_exists(self) -> None:
        store = _make_store()
        db = MagicMock()
        db.artifacts.get_by_session_path = MagicMock(
            return_value={
                "content_hash": "sha256-abc",
                "version": 2,
                "task_id": "plan",
            }
        )
        store._get_db.return_value = db
        resolver = _make_resolver(store=store)

        result = resolver.build_artifact_handoff_manifest("node-1", ["plan.md"])

        assert len(result) == 1
        assert result[0]["exists"] is True
        assert result[0]["sha256"] == "sha256-abc"
        assert result[0]["version"] == 2
        assert result[0]["producer_stage"] == "plan"

    def test_fallback_to_session_artifact(self) -> None:
        store = _make_store()
        db = MagicMock()
        db.artifacts.get_by_session_path = MagicMock(return_value=None)
        store._get_db.return_value = db
        store.load_artifact.return_value = "# Plan content"

        resolver = _make_resolver(store=store)

        result = resolver.build_artifact_handoff_manifest("node-1", ["plan.md"])

        assert len(result) == 1
        assert result[0]["exists"] is True
        assert result[0]["version"] == "unknown"
        expected_hash = hashlib.sha256("# Plan content".encode("utf-8")).hexdigest()
        assert result[0]["sha256"] == expected_hash

    def test_manifest_sorted_by_path(self) -> None:
        store = _make_store()
        db = MagicMock()
        db.artifacts.get_by_session_path = MagicMock(return_value=None)
        store._get_db.return_value = db
        store.load_artifact.return_value = None

        resolver = _make_resolver(store=store)

        result = resolver.build_artifact_handoff_manifest(
            "node-1", ["z-artifact.md", "a-artifact.md"]
        )

        paths = [entry["path"] for entry in result]
        assert paths == ["a-artifact.md", "z-artifact.md"]


class TestCheckRequiredInputs:
    def test_all_present_returns_empty(self) -> None:
        store = _make_store()
        db = MagicMock()
        db.artifacts.get_by_session_path = MagicMock(
            return_value={"content_hash": "abc", "version": 1, "task_id": "plan"}
        )
        store._get_db.return_value = db
        resolver = _make_resolver(store=store)

        missing = resolver.check_required_inputs("node-1", ["plan.md"])

        assert missing == []

    def test_missing_returns_paths(self) -> None:
        store = _make_store()
        db = MagicMock()
        db.artifacts.get_by_session_path = MagicMock(return_value=None)
        store._get_db.return_value = db
        store.load_artifact.return_value = None
        resolver = _make_resolver(store=store)

        missing = resolver.check_required_inputs("node-1", ["plan.md", "design.md"])

        assert "plan.md" in missing
        assert "design.md" in missing
