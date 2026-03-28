"""Tests for the generic CRUD router factory."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pixl_api.routes._crud import FilterParam, make_crud_router
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Test schemas
# ---------------------------------------------------------------------------


class CreateWidgetRequest(BaseModel):
    title: str
    colour: str = "red"


class UpdateWidgetRequest(BaseModel):
    title: str | None = None
    colour: str | None = None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_WIDGETS: dict[str, dict[str, Any]] = {}


def _make_backlog() -> MagicMock:
    """Return a mock backlog store wired to an in-memory dict."""
    backlog = MagicMock()

    def list_widgets(
        *, status: str | None = None, colour: str | None = None
    ) -> list[dict[str, Any]]:
        results = list(_WIDGETS.values())
        if status:
            results = [w for w in results if w.get("status") == status]
        if colour:
            results = [w for w in results if w.get("colour") == colour]
        return results

    def get_widget(widget_id: str) -> dict[str, Any] | None:
        return _WIDGETS.get(widget_id)

    def add_widget(**kwargs: Any) -> dict[str, Any]:
        wid = f"w-{len(_WIDGETS) + 1}"
        widget = {"id": wid, "status": "active", **kwargs}
        _WIDGETS[wid] = widget
        return widget

    def update_widget(widget_id: str, **fields: Any) -> bool:
        if widget_id not in _WIDGETS:
            return False
        _WIDGETS[widget_id].update(fields)
        return True

    def remove_widget(widget_id: str) -> bool:
        return _WIDGETS.pop(widget_id, None) is not None

    def update_widget_status(
        widget_id: str, new_status: str, *, note: str | None = None
    ) -> dict[str, Any] | None:
        if widget_id not in _WIDGETS:
            return None
        _WIDGETS[widget_id]["status"] = new_status
        return _WIDGETS[widget_id]

    backlog.list_widgets = list_widgets
    backlog.get_widget = get_widget
    backlog.add_widget = add_widget
    backlog.update_widget = update_widget
    backlog.remove_widget = remove_widget
    backlog.update_widget_status = update_widget_status

    return backlog


def _make_events() -> MagicMock:
    events = MagicMock()
    events.get_entity_history.return_value = [{"event": "created"}]
    events.get_history.return_value = [{"transition": "active->done"}]
    return events


def _make_db() -> MagicMock:
    db = MagicMock()
    db.backlog = _make_backlog()
    db.events = _make_events()
    return db


@pytest.fixture(autouse=True)
def _reset_widgets() -> None:
    _WIDGETS.clear()


@pytest.fixture()
def client() -> TestClient:
    mock_db = _make_db()

    router = make_crud_router(
        prefix="/projects/{project_id}/widgets",
        tag="widgets",
        entity_name="widget",
        entity_id_param="widget_id",
        list_method="list_widgets",
        get_method="get_widget",
        create_method="add_widget",
        update_method="update_widget",
        remove_method="remove_widget",
        create_schema=CreateWidgetRequest,
        update_schema=UpdateWidgetRequest,
        list_filters=[
            FilterParam(name="colour", description="Filter by colour"),
        ],
    )

    app = FastAPI()

    # Register error handlers so EntityNotFoundError -> 404 JSON response
    from pixl_api.deps import get_project_db
    from pixl_api.foundation.api.errors import register_error_handlers

    register_error_handlers(app)
    app.dependency_overrides[get_project_db] = lambda: mock_db
    app.include_router(router)

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestList:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/projects/p1/widgets")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_items(self, client: TestClient) -> None:
        client.post("/projects/p1/widgets", json={"title": "A"})
        client.post("/projects/p1/widgets", json={"title": "B"})
        resp = client.get("/projects/p1/widgets")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_with_filter(self, client: TestClient) -> None:
        client.post("/projects/p1/widgets", json={"title": "A", "colour": "red"})
        client.post("/projects/p1/widgets", json={"title": "B", "colour": "blue"})
        resp = client.get("/projects/p1/widgets?colour=blue")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["colour"] == "blue"

    def test_list_with_status_filter(self, client: TestClient) -> None:
        client.post("/projects/p1/widgets", json={"title": "A"})
        resp = client.get("/projects/p1/widgets?status=active")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_pagination(self, client: TestClient) -> None:
        for i in range(5):
            client.post("/projects/p1/widgets", json={"title": f"W{i}"})
        resp = client.get("/projects/p1/widgets?limit=2&offset=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCreate:
    def test_create_returns_201(self, client: TestClient) -> None:
        resp = client.post("/projects/p1/widgets", json={"title": "New Widget"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "New Widget"
        assert "id" in body

    def test_create_with_defaults(self, client: TestClient) -> None:
        resp = client.post("/projects/p1/widgets", json={"title": "Default"})
        assert resp.status_code == 201
        assert resp.json()["colour"] == "red"


class TestGet:
    def test_get_existing(self, client: TestClient) -> None:
        created = client.post("/projects/p1/widgets", json={"title": "X"}).json()
        resp = client.get(f"/projects/p1/widgets/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "X"

    def test_get_not_found(self, client: TestClient) -> None:
        resp = client.get("/projects/p1/widgets/nonexistent")
        assert resp.status_code == 404


class TestUpdate:
    def test_put_updates_fields(self, client: TestClient) -> None:
        created = client.post("/projects/p1/widgets", json={"title": "Old"}).json()
        resp = client.put(
            f"/projects/p1/widgets/{created['id']}",
            json={"title": "New"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    def test_patch_updates_fields(self, client: TestClient) -> None:
        created = client.post("/projects/p1/widgets", json={"title": "Old"}).json()
        resp = client.patch(
            f"/projects/p1/widgets/{created['id']}",
            json={"colour": "green"},
        )
        assert resp.status_code == 200
        assert resp.json()["colour"] == "green"

    def test_update_not_found(self, client: TestClient) -> None:
        resp = client.put(
            "/projects/p1/widgets/nonexistent",
            json={"title": "X"},
        )
        assert resp.status_code == 404


class TestDelete:
    def test_delete_existing(self, client: TestClient) -> None:
        created = client.post("/projects/p1/widgets", json={"title": "Doomed"}).json()
        resp = client.delete(f"/projects/p1/widgets/{created['id']}")
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}

    def test_delete_not_found(self, client: TestClient) -> None:
        resp = client.delete("/projects/p1/widgets/nonexistent")
        assert resp.status_code == 404


class TestTransition:
    def test_transition_fallback_success(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When TransitionEngine is unavailable, fallback to direct status update."""
        # Hide the engine module so the ImportError fallback path runs.
        import sys

        monkeypatch.setitem(sys.modules, "pixl.state.engine", None)

        created = client.post("/projects/p1/widgets", json={"title": "T"}).json()
        resp = client.post(
            f"/projects/p1/widgets/{created['id']}/transition",
            json={"to_status": "done", "reason": "completed"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["old_status"] == "active"
        assert body["new_status"] == "done"

    def test_transition_not_found(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sys

        monkeypatch.setitem(sys.modules, "pixl.state.engine", None)

        resp = client.post(
            "/projects/p1/widgets/nonexistent/transition",
            json={"to_status": "done"},
        )
        assert resp.status_code == 404


class TestHistory:
    def test_history_returns_events(self, client: TestClient) -> None:
        created = client.post("/projects/p1/widgets", json={"title": "H"}).json()
        resp = client.get(f"/projects/p1/widgets/{created['id']}/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_transitions_returns_events(self, client: TestClient) -> None:
        created = client.post("/projects/p1/widgets", json={"title": "H"}).json()
        resp = client.get(f"/projects/p1/widgets/{created['id']}/transitions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestRouteCount:
    """Ensure the factory generates the expected number of routes."""

    def test_standard_route_count(self) -> None:
        router = make_crud_router(
            prefix="/projects/{project_id}/things",
            tag="things",
            entity_name="thing",
            entity_id_param="thing_id",
            list_method="list_things",
            get_method="get_thing",
            create_method="add_thing",
            update_method="update_thing",
            remove_method="remove_thing",
            create_schema=CreateWidgetRequest,
            update_schema=UpdateWidgetRequest,
        )
        # list, create, get, put, patch, delete, transition, history, transitions
        # PUT and PATCH are separate routes
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert len(paths) == 9
