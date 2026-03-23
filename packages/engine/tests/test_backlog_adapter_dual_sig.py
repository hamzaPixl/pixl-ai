"""Tests for dual-signature update_epic() and update_roadmap() on BacklogStoreAdapter."""

from pathlib import Path

import pytest
from pixl.storage.backlog_adapter import BacklogStoreAdapter


@pytest.fixture()
def store(tmp_path: Path) -> BacklogStoreAdapter:
    """Create a BacklogStoreAdapter backed by a temp project directory."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    return BacklogStoreAdapter(tmp_path)


class TestUpdateEpicDualSignature:
    """update_epic() accepts either an Epic model or (epic_id, **fields)."""

    def test_update_epic_by_id_and_fields(self, store: BacklogStoreAdapter) -> None:
        epic = store.add_epic(title="Original Title", original_prompt="build it")

        result = store.update_epic(epic.id, title="New Title")

        assert result is True
        updated = store.get_epic(epic.id)
        assert updated is not None
        assert updated.title == "New Title"

    def test_update_epic_by_model(self, store: BacklogStoreAdapter) -> None:
        epic = store.add_epic(title="Original Title", original_prompt="build it")
        epic.title = "Model Updated"

        result = store.update_epic(epic)

        assert result is True
        updated = store.get_epic(epic.id)
        assert updated is not None
        assert updated.title == "Model Updated"

    def test_update_epic_status_by_id(self, store: BacklogStoreAdapter) -> None:
        epic = store.add_epic(title="Epic", original_prompt="prompt")

        store.update_epic(epic.id, status="in_progress")

        updated = store.get_epic(epic.id)
        assert updated is not None
        assert updated.status.value == "in_progress"


class TestUpdateRoadmapDualSignature:
    """update_roadmap() accepts either a Roadmap model or (roadmap_id, **fields)."""

    def test_update_roadmap_by_id_and_fields(self, store: BacklogStoreAdapter) -> None:
        roadmap = store.add_roadmap(title="Original", original_prompt="plan")

        result = store.update_roadmap(roadmap.id, title="Updated Roadmap")

        assert result is True
        updated = store.get_roadmap(roadmap.id)
        assert updated is not None
        assert updated.title == "Updated Roadmap"

    def test_update_roadmap_by_model(self, store: BacklogStoreAdapter) -> None:
        roadmap = store.add_roadmap(title="Original", original_prompt="plan")
        roadmap.title = "Model Updated"

        result = store.update_roadmap(roadmap)

        assert result is True
        updated = store.get_roadmap(roadmap.id)
        assert updated is not None
        assert updated.title == "Model Updated"

    def test_update_roadmap_status_by_id(self, store: BacklogStoreAdapter) -> None:
        roadmap = store.add_roadmap(title="Roadmap", original_prompt="plan")

        store.update_roadmap(roadmap.id, status="in_progress")

        updated = store.get_roadmap(roadmap.id)
        assert updated is not None
        assert updated.status.value == "in_progress"
