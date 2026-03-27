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
    name: str
    description: str
    path: str
    created_at: str | None = None
