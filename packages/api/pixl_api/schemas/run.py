"""Pydantic request/response models for workflow run endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    """Classify a user prompt to determine the best workflow."""

    prompt: str = Field(min_length=1, max_length=50000, description="User prompt to classify")
    model: str | None = Field(None, description="Optional model override for classification")


class ClassifyResponse(BaseModel):
    """Result of prompt classification — matches engine RouterResult shape."""

    kind: str = Field(description="Work kind: feature, epic, roadmap, bug")
    confidence: float | None = Field(
        None, description="Classification confidence (null for keyword-based)"
    )
    title: str = Field(description="Suggested title for the work item")
    suggested_workflow: str = Field(description="Suggested workflow ID")
    estimated_features: int = Field(default=1, description="Estimated number of features")
    why: list[str] = Field(default_factory=list, description="Reasoning for classification")
    risk_flags: list[str] = Field(default_factory=list, description="Identified risk flags")
    suggested_sub_workflows: list[str] = Field(
        default_factory=list, description="Suggested sub-workflows"
    )


class RunConfirmRequest(BaseModel):
    """Start a workflow execution from a prompt."""

    prompt: str = Field(
        min_length=1, max_length=50000, description="Prompt describing what to build"
    )
    kind: str = Field(default="feature", description="Work kind: feature, epic, roadmap")
    title: str = Field(default="", description="Title for the work item")
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


class RunStartResponse(BaseModel):
    """Response when workflow execution starts (streaming mode)."""

    session_id: str
    entity_id: str
    entity_kind: str
    execution_feature_id: str | None = None
    status: str = "running"


class RunFeatureRequest(BaseModel):
    """Run a workflow against an existing feature."""

    workflow_id: str | None = Field(
        None, description="Explicit workflow ID; auto-classified if omitted"
    )
    skip_approval: bool = Field(True, description="Auto-approve gates during execution")
