"""Sandbox project tracking store.

Tracks sandbox projects and their operations in the local pixl.db.
Projects are created/managed via the CLI sandbox commands and
communicate with remote sandbox workers over HTTP.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pixl.storage.db.base import BaseStore


class SandboxDB(BaseStore):
    """Store for sandbox_projects and sandbox_operations tables."""

    def create_project(
        self,
        project_id: str,
        sandbox_url: str,
        *,
        repo_url: str | None = None,
        branch: str = "main",
        env_keys: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new sandbox project record."""
        now = datetime.now(UTC).isoformat()
        with self._db.write() as conn:
            conn.execute(
                """INSERT INTO sandbox_projects
                   (id, sandbox_url, repo_url, branch, env_keys_json, config_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id,
                    sandbox_url,
                    repo_url,
                    branch,
                    json.dumps(env_keys or []),
                    json.dumps(config or {}),
                    now,
                ),
            )
            conn.commit()
        return self.get_project(project_id)  # type: ignore[return-value]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get a sandbox project by ID."""
        row = self._conn.execute(
            "SELECT * FROM sandbox_projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        return self._deserialize_json(
            result,
            {"env_keys_json": "env_keys", "config_json": "config"},
            defaults={"env_keys": [], "config": {}},
        )

    def list_projects(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List sandbox projects, optionally filtered by status."""
        where, params = self._build_where({"status": status})
        query = f"SELECT * FROM sandbox_projects {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            r = dict(row)
            self._deserialize_json(
                r,
                {"env_keys_json": "env_keys", "config_json": "config"},
                defaults={"env_keys": [], "config": {}},
            )
            results.append(r)
        return results

    def update_project(self, project_id: str, **fields: Any) -> dict[str, Any] | None:
        """Update sandbox project fields."""
        if not fields:
            return self.get_project(project_id)

        # Serialize JSON fields
        if "env_keys" in fields:
            fields["env_keys_json"] = json.dumps(fields.pop("env_keys"))
        if "config" in fields:
            fields["config_json"] = json.dumps(fields.pop("config"))

        fields["updated_at"] = datetime.now(UTC).isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [project_id]
        with self._db.write() as conn:
            conn.execute(
                f"UPDATE sandbox_projects SET {set_clause} WHERE id = ?",  # noqa: S608
                values,
            )
            conn.commit()
        return self.get_project(project_id)

    def log_operation(
        self,
        project_id: str,
        operation: str,
        *,
        status: str = "started",
        duration_ms: int | None = None,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> int:
        """Log a sandbox operation. Returns the operation ID."""
        now = datetime.now(UTC).isoformat()
        with self._db.write() as conn:
            cursor = conn.execute(
                """INSERT INTO sandbox_operations
                   (project_id, operation, status, duration_ms,
                    request_json, response_json, error, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id,
                    operation,
                    status,
                    duration_ms,
                    json.dumps(request) if request else None,
                    json.dumps(response) if response else None,
                    error,
                    now,
                ),
            )
            conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

