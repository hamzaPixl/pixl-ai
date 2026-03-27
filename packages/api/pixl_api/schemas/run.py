"""Pydantic request/response models for workflow run endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    """Classify a user prompt to determine the best workflow."""

    prompt: str = Field(min_length=1, max_length=2000, description="User prompt to classify")


class ClassifyResponse(BaseModel):
    """Result of prompt classification."""

    workflow_id: str
    workflow_name: str
    confidence: float | None = None


class RunConfirmRequest(BaseModel):
    """Start a workflow execution from a prompt."""

    prompt: str = Field(
        min_length=1, max_length=5000, description="Prompt describing what to build"
    )
    workflow_id: str | None = Field(
        None, description="Explicit workflow ID; auto-classified if omitted"
    )
    skip_approval: bool = Field(True, description="Auto-approve gates during execution")


class RunResponse(BaseModel):
    """Summary returned after workflow execution completes (non-streaming)."""

    session_id: str
    feature_id: str
    workflow_id: str
    status: str
    steps: int = 0


class RunFeatureRequest(BaseModel):
    """Run a workflow against an existing feature."""

    workflow_id: str | None = Field(
        None, description="Explicit workflow ID; auto-classified if omitted"
    )
    skip_approval: bool = Field(True, description="Auto-approve gates during execution")
