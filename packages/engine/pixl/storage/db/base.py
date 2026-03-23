"""Base store class for SQLite-backed domain stores.

Provides the common __init__(db) + _conn property boilerplate,
plus shared helpers for JSON deserialization and WHERE clause building.

All domain stores (BacklogDB, ArtifactDB, etc.) should extend BaseStore
to avoid repeating connection wiring in every file.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB


class BaseStore:
    """Base class for PixlDB-backed stores.

    Subclasses get:
    - ``self._db`` reference to the PixlDB instance
    - ``self._conn`` property returning the thread-local SQLite connection
    - ``_deserialize_json()`` for batch JSON field parsing
    - ``_build_where()`` for dynamic WHERE clause construction
    """

    def __init__(self, db: PixlDB) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        """Get the thread-local connection from PixlDB."""
        return self._db.conn

    @staticmethod
    def _deserialize_json(
        row: dict[str, Any], mappings: dict[str, str], *, defaults: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Deserialize JSON string fields in a row dict.

        Args:
            row: Mutable dict (typically from sqlite3.Row).
            mappings: ``{source_json_key: output_key}`` pairs.
                      The source key is removed after parsing.
            defaults: Optional ``{output_key: default_value}`` for
                      NULL / decode-error cases.  Falls back to ``None``.

        Returns:
            The mutated *row* for chaining convenience.
        """
        _defaults = defaults or {}
        for src, dst in mappings.items():
            raw = row.pop(src, None)
            if raw:
                try:
                    row[dst] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    row[dst] = _defaults.get(dst)
            else:
                row[dst] = _defaults.get(dst)
        return row

    @staticmethod
    def _parse_json_dict(value: str | None) -> dict[str, Any]:
        """Parse a JSON string to dict, returning {} on None/error/non-dict."""
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _build_where(filters: dict[str, Any]) -> tuple[str, list[Any]]:
        """Build a WHERE clause from a dict of column=value filters.

        ``None`` values are skipped (no filter applied for that column).

        Returns:
            ``(where_clause, params)`` — the clause includes the ``WHERE``
            keyword, or is an empty string when no filters matched.
        """
        conditions: list[str] = []
        params: list[Any] = []
        for col, val in filters.items():
            if val is not None:
                conditions.append(f"{col} = ?")
                params.append(val)
        return (f"WHERE {' AND '.join(conditions)}" if conditions else "", params)
