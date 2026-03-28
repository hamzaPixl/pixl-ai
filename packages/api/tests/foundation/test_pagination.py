"""Tests for foundation.api.pagination."""

from __future__ import annotations

from pixl_api.foundation.api.pagination import PaginatedResponse, paginate_params


class TestPaginatedResponse:
    def test_create_with_items(self) -> None:
        resp = PaginatedResponse.create(items=["a", "b", "c"], total=10, limit=3, offset=0)
        assert resp.items == ["a", "b", "c"]
        assert resp.total == 10
        assert resp.limit == 3
        assert resp.offset == 0

    def test_serialization(self) -> None:
        resp = PaginatedResponse.create(items=[1, 2], total=5, limit=2, offset=2)
        data = resp.model_dump()
        assert data == {"items": [1, 2], "total": 5, "limit": 2, "offset": 2}


class TestPaginateParams:
    def test_defaults(self) -> None:
        limit, offset = paginate_params()
        assert limit == 50
        assert offset == 0

    def test_custom_values(self) -> None:
        limit, offset = paginate_params(limit=10, offset=20)
        assert limit == 10
        assert offset == 20

    def test_clamps_limit(self) -> None:
        limit, _ = paginate_params(limit=500)
        assert limit == 100

    def test_clamps_negative_offset(self) -> None:
        _, offset = paginate_params(offset=-5)
        assert offset == 0
