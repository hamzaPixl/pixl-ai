"""Pagination utilities for API responses."""

from __future__ import annotations

from pydantic import BaseModel

MAX_LIMIT = 100
DEFAULT_LIMIT = 50


class PaginatedResponse[T](BaseModel):
    """Generic paginated response wrapper."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        limit: int,
        offset: int,
    ) -> PaginatedResponse[T]:
        return cls(items=items, total=total, limit=limit, offset=offset)


def paginate_params(limit: int = DEFAULT_LIMIT, offset: int = 0) -> tuple[int, int]:
    """Normalize and clamp pagination parameters.

    Returns (limit, offset) with limit clamped to [1, MAX_LIMIT]
    and offset clamped to >= 0.
    """
    clamped_limit = max(1, min(limit, MAX_LIMIT))
    clamped_offset = max(0, offset)
    return clamped_limit, clamped_offset
