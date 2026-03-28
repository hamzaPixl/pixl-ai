"""Pydantic request/response models for project endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    project_root: str | None = None


class InitProjectRequest(BaseModel):
    project_name: str | None = None


class ProjectResponse(BaseModel):
    id: str
    project_id: str = ""
    name: str
    project_name: str = ""
    description: str
    path: str
    project_root: str | None = None
    storage_dir: str = ""
    db_path: str | None = None
    storage_mode: str | None = None
    last_used_at: float | None = None
    created_at: str | None = None
