"""DB-backed workflow template store with versioning.

Stores workflow templates in SQLite with version tracking.
Each update bumps the version counter, giving a simple audit
trail of template evolution without requiring full event sourcing.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from pixl.storage.db.base import BaseStore


class WorkflowTemplateDB(BaseStore):
    """CRUD for workflow templates stored in SQLite."""

    def create(
        self,
        name: str,
        yaml_content: str,
        *,
        description: str | None = None,
        config: dict[str, Any] | None = None,
        source: str = "db",
    ) -> dict[str, Any]:
        """Create a new workflow template.

        Args:
            name: Template name (e.g., "tdd", "debug").
            yaml_content: Raw YAML content of the workflow.
            description: Optional human-readable description.
            config: Optional JSON-serializable configuration.
            source: Origin of the template ("db", "filesystem", "imported").

        Returns:
            The created template as a dict.
        """
        template_id = f"wft-{uuid.uuid4().hex[:8]}"
        with self._db.write() as conn:
            conn.execute(
                """INSERT INTO workflow_templates
                   (id, name, description, yaml_content, config_json, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    template_id,
                    name,
                    description,
                    yaml_content,
                    json.dumps(config or {}),
                    source,
                ),
            )
            conn.commit()
        return self.get(template_id)  # type: ignore[return-value]

    def get(self, template_id: str) -> dict[str, Any] | None:
        """Get a template by ID."""
        row = self._conn.execute(
            "SELECT * FROM workflow_templates WHERE id = ?", (template_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get the latest version of a template by name."""
        row = self._conn.execute(
            "SELECT * FROM workflow_templates WHERE name = ? ORDER BY version DESC LIMIT 1",
            (name,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def list_templates(
        self,
        source: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List all templates, optionally filtered by source.

        Args:
            source: Optional filter by source ("db", "filesystem", "imported").
            limit: Maximum number of results.

        Returns:
            List of template dicts, ordered by most recently updated.
        """
        where, params = self._build_where({"source": source})
        query = (
            f"SELECT * FROM workflow_templates {where} "
            "ORDER BY updated_at DESC, created_at DESC LIMIT ?"
        )
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update(
        self,
        template_id: str,
        *,
        yaml_content: str | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> bool:
        """Update a template, bumping its version.

        Args:
            template_id: ID of the template to update.
            yaml_content: New YAML content (if changing).
            description: New description (if changing).
            config: New config dict (if changing).

        Returns:
            True if the template was found and updated, False otherwise.
        """
        existing = self.get(template_id)
        if not existing:
            return False

        sets: list[str] = []
        params: list[Any] = []

        if yaml_content is not None:
            sets.append("yaml_content = ?")
            params.append(yaml_content)
        if description is not None:
            sets.append("description = ?")
            params.append(description)
        if config is not None:
            sets.append("config_json = ?")
            params.append(json.dumps(config))

        sets.append("version = version + 1")
        sets.append("updated_at = datetime('now')")
        params.append(template_id)

        with self._db.write() as conn:
            conn.execute(
                f"UPDATE workflow_templates SET {', '.join(sets)} WHERE id = ?",  # noqa: S608
                params,
            )
            conn.commit()
        return True

    def delete(self, template_id: str) -> bool:
        """Delete a template by ID.

        Returns:
            True if a row was deleted, False otherwise.
        """
        with self._db.write() as conn:
            cursor = conn.execute("DELETE FROM workflow_templates WHERE id = ?", (template_id,))
            conn.commit()
        return cursor.rowcount > 0

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert a sqlite3.Row to a dict with deserialized JSON fields."""
        result = dict(row)
        return self._deserialize_json(
            result,
            {"config_json": "config"},
            defaults={"config": {}},
        )
