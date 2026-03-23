"""YAML workflow configuration models.

This module defines Pydantic models for loading workflow definitions from YAML files.
The models map from the declarative YAML format to the existing ExecutionGraph system.

YAML Structure:
```yaml
id: workflow-id
name: Workflow Name
description: Human-readable description
version: 1.0.0

stages:
  - id: stage-id
    name: Stage Name
    agent: agent-name
    max_turns: 50
    type: task  # or "gate"
    timeout_minutes: 60
    required_artifacts: [artifact.md]
    outputs: [output1.md, output2.md]

loops:
  - id: loop-id
    from: source-stage
    to: target-stage
    trigger: failure  # success, failure, always
    max_iterations: 3
    condition: "has_bugs == true"

edges:
  stage-id: [next-stage, another-stage]  # Optional: explicit edges
```
"""

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ParameterOption(BaseModel):
    """Option for choice/checklist parameters."""

    id: str = Field(description="Option identifier")
    label: str = Field(description="Display label")
    default: bool = Field(default=False, description="Default selection state")


class ParameterConfig(BaseModel):
    """Configuration for an interactive parameter.

    Parameters are collected before workflow execution and injected
    into the workflow context for variable substitution.
    """

    id: str = Field(description="Parameter identifier (used in {{id}} substitution)")
    type: Literal["string", "text", "confirm", "choice", "checklist"] = Field(
        default="string",
        description="Parameter type determines the prompt style",
    )
    label: str = Field(description="Human-readable label for the prompt")
    description: str | None = Field(
        default=None,
        description="Help text shown below the prompt",
    )
    default: str | bool | None = Field(
        default=None,
        description="Default value (can use {{variable}} substitution)",
    )
    required: bool = Field(
        default=False,
        description="Whether the parameter must have a value",
    )
    options: list[str] | list[ParameterOption] | None = Field(
        default=None,
        description="Options for choice/checklist types",
    )
    advanced: bool = Field(
        default=False,
        description="If True, only shown when user requests advanced options",
    )
    condition: str | None = Field(
        default=None,
        description="PixlExpr condition for showing this parameter",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate parameter ID is snake_case (safe for template substitution)."""
        import re

        if not v:
            raise ValueError("Parameter ID cannot be empty")
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"Parameter ID '{v}' must be snake_case (lowercase, numbers, underscores)"
            )
        return v


class ArtifactNeed(BaseModel):
    """Declares how a stage needs a specific artifact in its context.

    Used within ContextNeeds to control artifact inclusion priority and
    section-level extraction instead of the default cheapest-layer selection.
    """

    name: str = Field(description="Artifact filename, e.g. 'plan.md'")
    priority: Literal["critical", "standard", "background"] = Field(
        default="standard",
        description=(
            "Inclusion priority: critical (full/excerpt preferred), "
            "standard (excerpt/summary), background (summary only)"
        ),
    )
    sections: list[str] | None = Field(
        default=None,
        description="Specific markdown sections to extract (e.g. ['Tasks', 'Testing Strategy'])",
    )
    max_lines: int | None = Field(
        default=None,
        description="Override default excerpt length for this artifact",
    )


class PredecessorNeed(BaseModel):
    """Declares what to include from a predecessor stage's structured output.

    Controls the detail level of predecessor context: summary (default),
    full payload, or specific fields from the payload dict.
    """

    stage_id: str = Field(description="Predecessor stage ID, e.g. 'tdd-plan'")
    include: Literal["summary", "full_payload", "specific_fields"] = Field(
        default="summary",
        description="Detail level for predecessor output inclusion",
    )
    fields: list[str] | None = Field(
        default=None,
        description="Payload field names to include (only with include='specific_fields')",
    )
    optional: bool = Field(
        default=False,
        description="If true, missing predecessor is silently skipped instead of warning",
    )


class ContextNeeds(BaseModel):
    """Declares what context a stage needs from the compiled prompt.

    This is an opt-in declaration on workflow stages that guides the
    UnifiedContextCompiler to include the right artifacts at the right
    detail level, with priority-aware budget allocation.

    When absent, the compiler falls back to the default behavior
    (required_artifacts with equal priority, all predecessors as summary).
    """

    artifacts: list[ArtifactNeed] = Field(
        default_factory=list,
        description="Artifact inclusion declarations with priority levels",
    )
    predecessors: list[PredecessorNeed] = Field(
        default_factory=list,
        description="Predecessor output inclusion declarations",
    )
    baton_emphasis: list[str] = Field(
        default_factory=list,
        description=(
            "Baton fields to render in full detail (others rendered compact). "
            "Valid: constraints, acceptance, decision_log, open_questions, work_scope, stage_hints"
        ),
    )
    include_source_files: list[str] = Field(
        default_factory=list,
        description=(
            "Project source file patterns to include from knowledge index "
            "(e.g. ['models/user.py', 'models/incident.py'])"
        ),
    )


class StageContract(BaseModel):
    """Declarative output contract for a workflow stage.

    After a task completes successfully, these constraints are validated.
    Failure results in TASK_FAILED with failure_kind="contract_violation".

    Example YAML:
        contract:
          must_write: [artifacts/plan.md, artifacts/spec.md]
          must_include_sections:
            artifacts/plan.md:
              - "Tasks"
              - "Verification|How to Verify|Testing"
          must_include_command_blocks: true
          must_update_files: [src/main.py]
          max_diff_lines: 500
          max_files_changed: 10
          artifact_schemas:
            artifacts/spec.json: schemas/spec-schema.json
    """

    must_write: list[str] = Field(
        default_factory=list,
        description="Files that must exist after stage completion",
    )
    must_include_sections: dict[str, list[str]] = Field(
        default_factory=dict,
        description="File -> required headings (pipe-separated aliases supported)",
    )
    must_include_command_blocks: bool = Field(
        default=False,
        description="Require fenced bash/shell blocks or $ prefixed lines in must_write files",
    )
    must_update_files: list[str] = Field(
        default_factory=list,
        description="Files that must show in git diff from baseline commit",
    )
    max_diff_lines: int | None = Field(
        default=None,
        description="Max diff size (insertions + deletions) from baseline",
    )
    max_files_changed: int | None = Field(
        default=None,
        description="Max file count in diff from baseline",
    )
    artifact_schemas: dict[str, str] = Field(
        default_factory=dict,
        description="Artifact path -> JSON schema path for validation",
    )
    detect_stubs: bool = Field(
        default=False,
        description=(
            "Scan output files for stub/placeholder patterns (TODO, NotImplementedError, etc.)"
        ),
    )
    require_regression_test: bool = Field(
        default=False,
        description=(
            "Require at least one test file in must_write or must_update_files (for bug-fix loops)"
        ),
    )
    context_budget_pct: int | None = Field(
        default=None,
        description=(
            "Max percentage of context window plan output should target (e.g., 50)."
            " Warning emitted if exceeded."
        ),
    )
    verify_success_criteria: bool = Field(
        default=False,
        description=(
            "Run goal-backward verification against feature success_criteria after stage completion"
        ),
    )
    structured_output: bool = Field(
        default=False,
        description="Require structured <pixl_output> envelope from this stage",
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Skill names that must be invoked during the stage session "
            "(e.g. ['/ddd-pattern', '/pydantic-api-endpoint']). "
            "Validated by scanning the session transcript for Skill tool invocations."
        ),
    )
    required_agents: list[str] = Field(
        default_factory=list,
        description=(
            "Agent subagent_type values that must appear in the session transcript "
            "(e.g. ['pixl-crew:backend-engineer']). "
            "Validated by scanning for Agent tool invocations with matching subagent_type."
        ),
    )
    scope_boundary: list[str] = Field(
        default_factory=list,
        description=(
            "Glob patterns of files the stage may edit (e.g. ['console/**', 'tests/e2e/**']). "
            "If non-empty, any files changed outside these patterns trigger a contract violation."
        ),
    )
    forbidden_paths: list[str] = Field(
        default_factory=list,
        description=(
            "Glob patterns of files the stage must NOT edit (e.g. ['*.lock', 'uv.lock']). "
            "Takes precedence over scope_boundary."
        ),
    )


class WorkflowStageConfig(BaseModel):
    """Configuration for a single workflow stage.

    This maps to either a Task or Gate node in the ExecutionGraph.
    Stages can either be inline (with id/name) or block references (with use).
    """

    # Stage identification (required for inline stages, empty for block refs)
    id: str = Field(default="", description="Unique stage identifier (kebab-case)")
    name: str = Field(default="", description="Human-readable stage name")

    # Block reference fields
    use: str | None = Field(default=None, description="Block ID to expand in place")
    prefix: str = Field(default="", description="Prefix for expanded stage IDs")
    agent: str = Field(default="default", description="Agent to execute this stage")
    max_turns: int = Field(default=50, description="Max SDK turns for this stage")
    type: Literal["task", "gate", "hook", "sub_workflow"] = Field(
        default="task", description="Stage type: task, gate, hook, or sub_workflow"
    )
    sub_workflow: str | None = Field(
        default=None,
        description="Workflow ID to invoke as sub-workflow (required when type=sub_workflow)",
    )
    hook: str | None = Field(default=None, description="Hook ID (required when type=hook)")
    hook_params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters for hook function"
    )
    timeout_minutes: int | None = Field(
        default=None, description="Gate timeout in minutes (gate type only)"
    )
    timeout_policy: Literal["reject", "cancel", "auto"] = Field(
        default="reject",
        description="Gate timeout behavior: reject (safe), cancel session, or auto-approve",
    )
    required_artifacts: list[str] = Field(
        default_factory=list,
        description="Artifact patterns that must exist before gate approval",
    )
    outputs: list[str] = Field(
        default_factory=list,
        description="Expected output artifact patterns from this stage",
    )
    prompt: str | None = Field(
        default=None,
        description="Inline prompt template for this stage",
    )
    prompt_ref: str | None = Field(
        default=None,
        description="Reference to shared prompt template (e.g., 'templates/validate-output')",
    )
    prompt_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Additional variables for prompt template substitution",
    )
    prompt_template: str | None = Field(
        default=None,
        description="Deprecated: Use 'prompt' or 'prompt_ref' instead",
    )
    description: str = Field(default="", description="Stage description (for gates)")
    contract: StageContract | None = Field(
        default=None,
        description="Output contract validated after stage completion",
    )
    freeze_artifacts: list[str] = Field(
        default_factory=list,
        description="Artifact paths to freeze (hash-lock) at gate approval",
    )
    output_schema: str | None = Field(
        default=None,
        description="JSON Schema path for validating structured output payload",
    )
    context_needs: ContextNeeds | None = Field(
        default=None,
        description=(
            "Declares what context this stage needs from the compiled prompt. "
            "Controls artifact priority, section extraction, predecessor detail "
            "level, and baton emphasis. Falls back to default behavior when absent."
        ),
    )
    change_request_target: str | None = Field(
        default=None,
        description="Gate ID whose frozen artifacts this stage may modify",
    )
    transitions: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Entity state transitions triggered by stage events. "
            "Keys: on_start, on_complete, on_failure. "
            "Values: target status string or dict with 'status' and optional 'note'."
        ),
    )
    exit_point: str | None = Field(
        default=None,
        description=(
            "Optional marker declaring this stage as a valid loop target. "
            "Used with block reference tokens like '{implement}' to enable explicit "
            "cross-block loop resolution. Example: 'implement' marks this as the "
            "implement stage for review iteration loops."
        ),
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate stage ID is kebab-case (if provided)."""
        if not v:
            # Empty ID is allowed for block references (validated in model_validator)
            return v
        # Allow alphanumeric, hyphen, underscore
        import re

        if not re.match(r"^[a-z][a-z0-9_-]*$", v):
            raise ValueError(f"Stage ID '{v}' must be kebab-case (lowercase, hyphens, underscores)")
        return v

    @model_validator(mode="after")
    def validate_stage_or_block(self) -> "WorkflowStageConfig":
        """Ensure stage has either id/name OR use, not both."""
        if self.use:
            # Block reference - id/name should be empty
            if self.id or self.name:
                raise ValueError(
                    f"Block reference (use='{self.use}') cannot have id or name. "
                    "Use 'prefix' to customize expanded stage IDs."
                )
            return self
        # Inline stage - id and name required
        if not self.id or not self.name:
            raise ValueError("Inline stage must have both id and name (or use a block)")
        # Hook stages must specify hook ID
        if self.type == "hook" and not self.hook:
            raise ValueError("Hook stages must specify 'hook' field")
        # Sub-workflow stages must specify sub_workflow ID
        if self.type == "sub_workflow" and not self.sub_workflow:
            raise ValueError("Sub-workflow stages must specify 'sub_workflow' field")
        return self


class LoopConfig(BaseModel):
    """Configuration for a loop constraint in the workflow.

    Defines a back-edge that creates a loop, with iteration limits.

    In YAML, use 'from' key. In Python, use the 'from_' attribute.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Unique loop identifier")
    from_: str = Field(
        default="from",
        alias="from",
        description="Source stage ID (where loop exits)",
    )
    to: str = Field(description="Target stage ID (where loop re-enters)")
    trigger: Literal["success", "failure", "always", "condition"] = Field(
        default="failure",
        description="Which edge trigger activates this loop",
    )
    max_iterations: int = Field(default=3, description="Maximum loop iterations")
    condition: str | None = Field(
        default=None,
        description="Optional PixlExpr condition for loop entry",
    )

    @field_validator("max_iterations")
    @classmethod
    def validate_max_iterations(cls, v: int) -> int:
        """Validate max iterations is positive."""
        if v < 1:
            raise ValueError("max_iterations must be at least 1")
        if v > 100:
            raise ValueError("max_iterations cannot exceed 100")
        return v


class BlockConfig(BaseModel):
    """A reusable block of workflow stages.

    Blocks are YAML files stored in:
    - src/pixl/assets/workflows/blocks/ (bundled)
    - ~/.pixl/workflows/blocks/ (global user library)
    - .pixl/workflows/blocks/ (project-specific)

    Example:
    ```yaml
    id: init
    name: Initialization Block
    description: Build context and refine prompt before implementation

    variables:
      design_file: "docs/features/{{feature_id}}.design.md"

    stages:
      - id: detect-context
        name: Detect Project Context
        agent: explorer
        max_turns: 15
        prompt: |
          Analyze the project structure...
    ```
    """

    id: str = Field(description="Block identifier (kebab-case)")
    name: str = Field(description="Human-readable block name")
    description: str = Field(default="", description="Block description")
    version: str = Field(default="1.0.0", description="Block version (semver)")

    # Block-level variables (can be overridden when using the block)
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Default variables for prompt substitution (overridable)",
    )

    # Stages contained in this block
    stages: list["WorkflowStageConfig"] = Field(
        default_factory=list,
        description="Stages that this block expands to",
    )

    # Optional edges within the block (defaults to sequential)
    edges: dict[str, list[str]] | None = Field(
        default=None,
        description="Explicit edges between stages within the block",
    )

    # Optional loop constraints within the block
    loops: list[LoopConfig] = Field(
        default_factory=list,
        description="Loop constraints within the block",
    )

    @field_validator("id")
    @classmethod
    def validate_block_id(cls, v: str) -> str:
        """Validate block ID is kebab-case."""
        if not v:
            raise ValueError("Block ID cannot be empty")
        import re

        if not re.match(r"^[a-z][a-z0-9_-]*$", v):
            raise ValueError(f"Block ID '{v}' must be kebab-case (lowercase, hyphens, underscores)")
        return v

    @field_validator("stages")
    @classmethod
    def validate_block_stages(cls, v: list["WorkflowStageConfig"]) -> list["WorkflowStageConfig"]:
        """Validate block has at least one stage with unique IDs."""
        if not v:
            raise ValueError("Block must have at least one stage")

        ids = [s.id for s in v if s.id]  # Only inline stages have IDs
        duplicates = [id_ for id_ in set(ids) if ids.count(id_) > 1]
        if duplicates:
            raise ValueError(f"Duplicate stage IDs in block: {duplicates}")

        return v

    @classmethod
    def from_yaml_file(cls, path: str | Path) -> "BlockConfig":
        """Load block configuration from a YAML file.

        Args:
            path: Path to YAML file

        Returns:
            BlockConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        import yaml

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Block file not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

        if not data:
            raise ValueError(f"Empty YAML file: {path}")

        return cls.model_validate(data)

    def to_yaml_file(self, path: str | Path) -> None:
        """Save block configuration to a YAML file.

        Args:
            path: Path to write YAML file
        """
        import yaml

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )


class ParallelConfig(BaseModel):
    """Configuration for parallel stage execution.

    Defines a set of stages that execute in parallel.
    """

    name: str = Field(description="Parallel group name")
    stages: list[str] = Field(description="Stage IDs to execute in parallel")


class WorkflowTier(StrEnum):
    """Workflow tier classification."""

    ORCHESTRATION = "orchestration"  # Multi-agent, gates, blocks, full lifecycle
    PLANNING = "planning"  # Produces artifacts (not code), decomposes scope
    TASK = "task"  # 2-5 stages, 0 gates, single-purpose, sub-invocable
    UTILITY = "utility"  # Lifecycle management, not feature work
    META = "meta"  # Generates pixl assets or project docs


class RoutingHints(BaseModel):
    """Routing hints for workflow discovery and sub-workflow composition."""

    auto_route: bool = Field(
        default=False,
        description="Whether this workflow can be auto-selected by the classifier",
    )
    sub_invocable: bool = Field(
        default=False,
        description="Whether this workflow can be invoked as a sub-workflow from a parent",
    )
    category: str = Field(
        default="general",
        description="Workflow category for grouping (e.g., frontend, backend, infrastructure)",
    )
    trigger_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that hint to the classifier this workflow is relevant",
    )


class WorkflowConfigYaml(BaseModel):
    """Top-level workflow configuration from YAML.

    This is the main model that maps from a YAML workflow definition.
    """

    id: str = Field(description="Workflow identifier (kebab-case)")
    name: str = Field(description="Human-readable workflow name")
    description: str = Field(default="", description="Workflow description")
    version: str = Field(default="1.0.0", description="Workflow version (semantic versioning)")
    tags: list[str] = Field(default_factory=list, description="Workflow tags for discovery")

    # Workflow format and session mode
    workflow_format: Literal["v2"] = Field(
        default="v2",
        description="v2: simplified phases with plugin delegation.",
    )
    session_mode: Literal["plugin"] = Field(
        default="plugin",
        description="plugin: delegate agent routing, skills, and permissions to installed plugin.",
    )

    # Tier and routing metadata
    tier: WorkflowTier | None = Field(
        default=None,
        description="Workflow tier: orchestration, planning, task, utility, or meta",
    )
    routing: RoutingHints = Field(
        default_factory=RoutingHints,
        description="Routing hints for classifier and sub-workflow composition",
    )

    # Global variables for prompt substitution
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Global variables available to all stage prompts",
    )

    # Interactive parameters (collected before execution)
    parameters: list[ParameterConfig] = Field(
        default_factory=list,
        description="Interactive parameters to collect before workflow execution",
    )

    # Stages (sequential by default)
    stages: list[WorkflowStageConfig] = Field(
        default_factory=list,
        description="Workflow stages in execution order",
    )

    loops: list[LoopConfig] = Field(
        default_factory=list,
        description="Loop constraints for iterative workflows",
    )

    # Parallel execution groups
    parallel: list[ParallelConfig] = Field(
        default_factory=list,
        description="Parallel stage groups",
    )

    # Optional explicit edges (defaults to sequential)
    edges: dict[str, list[str]] | None = Field(
        default=None,
        description="Explicit edges between stages (overrides sequential)",
    )

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=20,
        description=(
            "Global per-stage self-healing attempt budget. "
            "Includes the initial attempt (default: 3)."
        ),
    )

    # Optional metadata
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional workflow metadata",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate workflow ID."""
        if not v:
            raise ValueError("Workflow ID cannot be empty")
        import re

        if not re.match(r"^[a-z][a-z0-9_-]*$", v):
            raise ValueError(
                f"Workflow ID '{v}' must be kebab-case (lowercase, hyphens, underscores)"
            )
        return v

    @field_validator("stages")
    @classmethod
    def validate_stages(cls, v: list[WorkflowStageConfig]) -> list[WorkflowStageConfig]:
        """Validate stages have unique IDs and at least one entry stage.

        Block references (stages with 'use' field) are allowed and don't have IDs.
        """
        if not v:
            raise ValueError("Workflow must have at least one stage")

        # Only validate IDs for inline stages (not block references)
        ids = [s.id for s in v if s.id]  # Block refs have empty id
        duplicates = [id_ for id_ in set(ids) if ids.count(id_) > 1]
        if duplicates:
            raise ValueError(f"Duplicate stage IDs: {duplicates}")

        return v

    @field_validator("loops")
    @classmethod
    def validate_loops(cls, v: list[LoopConfig]) -> list[LoopConfig]:
        """Validate loop references point to existing stages."""
        # Note: This is a partial validation since we don't have stage IDs here
        # Full validation happens during conversion to ExecutionGraph
        return v

    def get_stage_by_id(self, stage_id: str) -> WorkflowStageConfig | None:
        """Get a stage configuration by ID."""
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        return None

    def get_entry_stages(self) -> list[str]:
        """Get entry stage IDs (stages with no incoming edges)."""
        if self.edges:
            # Stages not targeted by any edge are entry points
            all_targets = set()
            for targets in self.edges.values():
                all_targets.update(targets)
            return [s.id for s in self.stages if s.id not in all_targets]
        else:
            # Sequential: first stage is entry
            return [self.stages[0].id] if self.stages else []

    def get_exit_stages(self) -> list[str]:
        """Get exit stage IDs (stages with no outgoing edges)."""
        if self.edges:
            # Stages with no outgoing edges
            return [s.id for s in self.stages if s.id not in self.edges]
        else:
            # Sequential: last stage is exit
            return [self.stages[-1].id] if self.stages else []

    @classmethod
    def from_yaml_file(cls, path: str | Path) -> "WorkflowConfigYaml":
        """Load workflow configuration from a YAML file.

        Args:
            path: Path to YAML file

        Returns:
            WorkflowConfigYaml instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        import yaml

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

        if not data:
            raise ValueError(f"Empty YAML file: {path}")

        return cls.model_validate(data)

    def to_yaml_file(self, path: str | Path) -> None:
        """Save workflow configuration to a YAML file.

        Args:
            path: Path to write YAML file
        """
        import yaml

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )


__all__ = [
    "ArtifactNeed",
    "PredecessorNeed",
    "ContextNeeds",
    "ParameterOption",
    "ParameterConfig",
    "StageContract",
    "WorkflowStageConfig",
    "LoopConfig",
    "BlockConfig",
    "ParallelConfig",
    "WorkflowTier",
    "RoutingHints",
    "WorkflowConfigYaml",
]
