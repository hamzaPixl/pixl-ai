"""YAML workflow loader for Pixl.

This module loads workflow definitions from YAML files and converts them
to ExecutionGraph structures that can be executed by the GraphExecutor.

Features:
- Load workflows from multiple sources with cascading precedence:
  1. User global workflows: ~/.pixl/workflows/
  2. Project workflows: {project}/.pixl/workflows/ (overrides global)
  3. Bundled workflows: built-in to Pixl installation
- Validate workflow structure
- Convert YAML to ExecutionGraph with nodes, edges, and loop constraints
- Resolve models via the provider system
- Support for sequential, parallel, and custom edge workflows
"""

import logging
import warnings
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from pixl.config.block_loader import BlockLoader, BlockLoadError
from pixl.config.providers import load_providers_config
from pixl.models.workflow import (
    Edge,
    EdgeTrigger,
    ExecutionGraph,
    GateConfig,
    HookConfig,
    LoopConstraint,
    Node,
    NodeType,
    TaskConfig,
    TimeoutPolicy,
    WorkflowSnapshot,
    WorkflowTemplate,
)
from pixl.models.workflow_config import (
    LoopConfig,
    WorkflowConfigYaml,
    WorkflowStageConfig,
)
from pixl.paths import get_global_pixl_dir, get_workflows_dir

logger = logging.getLogger(__name__)

class WorkflowLoadError(Exception):
    """Error loading a workflow from YAML."""

    def __init__(self, message: str, path: str | Path | None = None):
        self.message = message
        self.path = str(path) if path else None
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.path:
            return f"Error loading workflow from {self.path}: {self.message}"
        return self.message

class ModelIssueSeverity(StrEnum):
    """Severity levels for model validation issues."""

    ERROR = "error"  # Blocks execution
    WARNING = "warning"  # Warns, allows execution
    INFO = "info"  # Resolution details (for validate command)

@dataclass
class ModelValidationIssue:
    """A single model validation issue."""

    stage_id: str
    severity: ModelIssueSeverity
    message: str
    model_input: str
    resolved_to: str | None = None
    suggestion: str | None = None

@dataclass
class ModelValidationResult:
    """Aggregated result of model validation."""

    issues: list[ModelValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == ModelIssueSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == ModelIssueSeverity.WARNING for i in self.issues)

    @property
    def errors(self) -> list[ModelValidationIssue]:
        return [i for i in self.issues if i.severity == ModelIssueSeverity.ERROR]

    @property
    def warnings(self) -> list[ModelValidationIssue]:
        return [i for i in self.issues if i.severity == ModelIssueSeverity.WARNING]

    def is_valid(self) -> bool:
        """True if no errors (warnings are acceptable)."""
        return not self.has_errors

class WorkflowLoader:
    """Loads and converts YAML workflows to ExecutionGraph.

    Workflow lookup follows a cascading precedence:
    1. User global: ~/.pixl/workflows/ (user's personal library)
    2. Project: {project}/.pixl/workflows/ (project-specific overrides)
    3. Bundled: built-in workflows (Pixl defaults)
    """

    # User global workflows directory
    GLOBAL_WORKFLOWS_DIR = get_global_pixl_dir() / "workflows"

    # Bundled assets shipped with the pixl package
    BUNDLED_ASSETS_DIR = Path(__file__).parent.parent / "assets"

    # Bundled workflows shipped with the pixl package
    BUNDLED_WORKFLOWS_DIR = BUNDLED_ASSETS_DIR / "workflows"

    def __init__(
        self,
        project_path: Path,
        global_workflows_dir: Path | None = None,
        bundled_workflows_dir: Path | None = None,
        global_blocks_dir: Path | None = None,
        bundled_blocks_dir: Path | None = None,
    ):
        """Initialize the workflow loader.

        Args:
            project_path: Path to the project root
            global_workflows_dir: Optional override for global workflows dir
                                 (primarily for testing)
            bundled_workflows_dir: Optional override for bundled workflows dir
                                  (primarily for testing)
            global_blocks_dir: Optional override for global blocks dir
                              (primarily for testing)
            bundled_blocks_dir: Optional override for bundled blocks dir
                               (primarily for testing)
        """
        self.project_path = project_path
        self.workflows_dir = get_workflows_dir(project_path)
        self.global_workflows_dir = global_workflows_dir or (get_global_pixl_dir() / "workflows")
        self.bundled_workflows_dir = bundled_workflows_dir or self.BUNDLED_WORKFLOWS_DIR

        self.providers_config = load_providers_config(project_path)

        self.block_loader = BlockLoader(
            project_path,
            global_blocks_dir=global_blocks_dir,
            bundled_blocks_dir=bundled_blocks_dir,
        )

        if global_workflows_dir is None:
            self.global_workflows_dir.mkdir(parents=True, exist_ok=True)

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all available YAML workflows from all sources.

        Returns:
            List of workflow metadata dictionaries with keys:
            - id: Workflow ID
            - name: Workflow name
            - description: Workflow description
            - path: Path to YAML file
            - version: Workflow version
            - source: Where the workflow comes from (global, project, bundled)
        """
        workflows: list[dict[str, Any]] = []

        # Helper to load workflows from a directory
        def load_from_dir(workflows_dir: Path, source: str) -> None:
            if not workflows_dir.exists():
                return
            for yaml_file in workflows_dir.glob("*.yaml"):
                try:
                    config = WorkflowConfigYaml.from_yaml_file(yaml_file)
                    existing = next((w for w in workflows if w["id"] == config.id), None)
                    validation = self.validate_models(config)
                    entry = {
                        "id": config.id,
                        "name": config.name,
                        "description": config.description,
                        "path": str(yaml_file),
                        "version": config.version,
                        "tags": config.tags,
                        "tier": config.tier.value if config.tier else None,
                        "routing": config.routing.model_dump() if config.routing else None,
                        "source": source,
                        "validation": validation,
                    }
                    if existing is None:
                        workflows.append(entry)
                    else:
                        # Higher-precedence source replaces lower
                        idx = workflows.index(existing)
                        workflows[idx] = entry
                except Exception as e:
                    logger.warning("Skipping invalid workflow %s: %s", yaml_file.name, e)
                    continue

        load_from_dir(self.bundled_workflows_dir, "bundled")
        load_from_dir(self.global_workflows_dir, "global")
        load_from_dir(self.workflows_dir, "project")

        return workflows

    def load_workflow(self, workflow_id: str | Path) -> WorkflowConfigYaml:
        """Load a workflow by ID or path.

        Lookup precedence:
        1. Direct path (if provided)
        2. Project workflows (.pixl/workflows/{id}.yaml)
        3. Global workflows (~/.pixl/workflows/{id}.yaml)
        4. Bundled workflows (built-in to Pixl)

        Args:
            workflow_id: Either a workflow ID (looks up in workflows dirs)
                        or a direct path to a YAML file

        Returns:
            WorkflowConfigYaml instance

        Raises:
            WorkflowLoadError: If workflow not found or invalid
        """
        # If it's a path, load directly
        path = Path(workflow_id)
        if path.exists() and path.is_file():
            return WorkflowConfigYaml.from_yaml_file(path)

        # Check project workflows (highest priority for IDs)
        yaml_file = self.workflows_dir / f"{workflow_id}.yaml"
        if yaml_file.exists():
            return WorkflowConfigYaml.from_yaml_file(yaml_file)

        # Check global workflows (second priority)
        yaml_file = self.global_workflows_dir / f"{workflow_id}.yaml"
        if yaml_file.exists():
            return WorkflowConfigYaml.from_yaml_file(yaml_file)

        # Check bundled workflows (lowest priority)
        yaml_file = self.bundled_workflows_dir / f"{workflow_id}.yaml"
        if yaml_file.exists():
            return WorkflowConfigYaml.from_yaml_file(yaml_file)

        # Not found anywhere
        raise WorkflowLoadError(
            f"Workflow '{workflow_id}' not found (checked: project, global, bundled)",
            self.workflows_dir,
        )

    def convert_to_graph(
        self,
        config: WorkflowConfigYaml,
        skip_model_validation: bool = False,
    ) -> ExecutionGraph:
        """Convert a YAML workflow config to an ExecutionGraph.

        Args:
            config: WorkflowConfigYaml instance
            skip_model_validation: If True, skip pre-build model validation

        Returns:
            ExecutionGraph ready for execution

        Raises:
            WorkflowLoadError: If conversion fails or model validation finds errors
        """
        # Expand block references before building graph
        expanded_stages, expanded_loops = self._expand_blocks(config.stages, config.loops)

        expanded_config = config.model_copy(
            update={"stages": expanded_stages, "loops": expanded_loops}
        )

        # Model validation (unless skipped)
        if not skip_model_validation:
            validation = self.validate_models(expanded_config)
            if validation.has_errors:
                error_msgs = [f"  [{i.stage_id}] {i.message}" for i in validation.errors]
                raise WorkflowLoadError("Model validation failed:\n" + "\n".join(error_msgs))
            if validation.has_warnings:
                for issue in validation.warnings:
                    warnings.warn(
                        f"[{issue.stage_id}] {issue.message}",
                        UserWarning,
                        stacklevel=2,
                    )

        nodes: dict[str, Node] = {}
        edges: dict[str, list[Edge]] = {}
        loop_constraints = []

        for i, stage in enumerate(expanded_stages):
            node = self._stage_to_node(stage, i)
            nodes[stage.id] = node

        if expanded_config.edges:
            # Use explicit edges
            for from_id, to_ids in expanded_config.edges.items():
                if from_id not in nodes:
                    raise WorkflowLoadError(f"Edge source '{from_id}' not found in stages")
                for to_id in to_ids:
                    if to_id not in nodes:
                        raise WorkflowLoadError(
                            f"Edge target '{to_id}' (from '{from_id}') not found in stages"
                        )
                    edges.setdefault(from_id, []).append(Edge(to=to_id, on=EdgeTrigger.SUCCESS))
        else:
            for i in range(len(expanded_stages) - 1):
                from_id = expanded_stages[i].id
                to_id = expanded_stages[i + 1].id
                edges.setdefault(from_id, []).append(Edge(to=to_id, on=EdgeTrigger.SUCCESS))

        for loop in expanded_loops:
            from_node = loop.from_  # Use from_ since 'from' is a reserved keyword
            if from_node not in nodes:
                raise WorkflowLoadError(f"Loop 'from' stage '{from_node}' not found in stages")
            if loop.to not in nodes:
                raise WorkflowLoadError(f"Loop 'to' stage '{loop.to}' not found in stages")

            trigger_map = {
                "success": EdgeTrigger.SUCCESS,
                "failure": EdgeTrigger.FAILURE,
                "always": EdgeTrigger.ALWAYS,
                "condition": EdgeTrigger.CONDITION,
            }
            edge_trigger = trigger_map.get(loop.trigger, EdgeTrigger.FAILURE)

            edges.setdefault(from_node, []).append(
                Edge(to=loop.to, on=edge_trigger, condition=loop.condition)
            )

            loop_constraints.append(
                LoopConstraint(
                    id=loop.id,
                    from_node=from_node,
                    to_node=loop.to,
                    max_iterations=loop.max_iterations,
                    edge_trigger=edge_trigger,
                )
            )

        for stage in expanded_stages:
            if stage.change_request_target:
                target_id = stage.change_request_target
                if target_id not in nodes:
                    raise WorkflowLoadError(
                        f"Stage '{stage.id}' has change_request_target "
                        f"'{target_id}' which does not exist in stages"
                    )
                target_node = nodes[target_id]
                if target_node.type != NodeType.GATE:
                    raise WorkflowLoadError(
                        f"Stage '{stage.id}' has change_request_target "
                        f"'{target_id}' which is not a gate stage"
                    )
                target_stage = next((s for s in expanded_stages if s.id == target_id), None)
                if target_stage and not target_stage.freeze_artifacts:
                    raise WorkflowLoadError(
                        f"Stage '{stage.id}' has change_request_target "
                        f"'{target_id}' which has no freeze_artifacts defined"
                    )

        graph = ExecutionGraph(nodes=nodes, edges=edges, loop_constraints=loop_constraints)

        # are not corrupted when a loop points back to an entry node)
        loop_edge_set = {(c.from_node, c.to_node) for c in loop_constraints}
        for from_id, edge_list in edges.items():
            if from_id in nodes:
                nodes[from_id].outbound_degree = sum(
                    1 for e in edge_list if (from_id, e.to) not in loop_edge_set
                )
            for edge in edge_list:
                if edge.to in nodes and (from_id, edge.to) not in loop_edge_set:
                    nodes[edge.to].inbound_degree += 1

        errors = graph.validate_graph()
        if errors:
            raise WorkflowLoadError("Graph validation failed:\n" + "\n".join(errors))

        return graph

    def convert_to_template(
        self,
        config: WorkflowConfigYaml,
        skip_model_validation: bool = False,
    ) -> WorkflowTemplate:
        """Convert a YAML workflow config to a WorkflowTemplate.

        Args:
            config: WorkflowConfigYaml instance
            skip_model_validation: If True, skip pre-build model validation

        Returns:
            WorkflowTemplate with snapshot

        Raises:
            WorkflowLoadError: If conversion fails
        """
        graph = self.convert_to_graph(config, skip_model_validation)

        # Expand blocks so the snapshot stores fully-resolved stage configs.
        # GraphExecutor needs every stage's prompt, prompt_ref, prompt_vars,
        # contract, and transitions — block references (use:) have empty IDs
        # and would be skipped during stage config lookup.
        expanded_stages, expanded_loops = self._expand_blocks(config.stages, config.loops)
        expanded_config = config.model_copy(
            update={"stages": expanded_stages, "loops": expanded_loops}
        )

        snapshot = WorkflowSnapshot(
            snapshot_schema_version=1,
            template_id=config.id,
            template_version=config.version,
            snapshot_hash="",  # Will be computed
            graph=graph,
            name=config.name,
            description=config.description,
            tags=config.tags,
            workflow_config=expanded_config.model_dump(exclude_none=True),
        )
        snapshot.update_hash()

        return WorkflowTemplate.from_snapshot(snapshot)

    def _stage_to_node(
        self,
        stage: WorkflowStageConfig,
        priority: int,
    ) -> Node:
        """Convert a stage config to a Node.

        Args:
            stage: WorkflowStageConfig
            priority: Node priority (execution order)

        Returns:
            Node instance
        """
        # Determine node type
        if stage.type == "gate":
            node_type = NodeType.GATE
        elif stage.type == "hook":
            node_type = NodeType.HOOK
        elif stage.type == "sub_workflow":
            node_type = NodeType.SUB_WORKFLOW
        else:
            node_type = NodeType.TASK

        # Sub-workflow nodes: store workflow ID in task_config metadata
        if node_type == NodeType.SUB_WORKFLOW:
            task_config = TaskConfig(
                agent="executor",
                model=None,
                max_turns=1,  # Execution handled by child GraphExecutor
            )
            return Node(
                id=stage.id,
                type=node_type,
                priority=priority,
                task_config=task_config,
                metadata={"sub_workflow": stage.sub_workflow or ""},
            )

        # Hook nodes: no model resolution, just hook config
        if node_type == NodeType.HOOK:
            hook_config = HookConfig(
                hook_id=stage.hook or "",
                params=stage.hook_params,
            )
            return Node(
                id=stage.id,
                type=node_type,
                priority=priority,
                hook_config=hook_config,
            )

        model = self._resolve_stage_model(stage)

        if node_type == NodeType.GATE:
            # Gate node
            timeout_policy_map = {
                "reject": TimeoutPolicy.REJECT,
                "cancel": TimeoutPolicy.CANCEL_SESSION,
                "auto": TimeoutPolicy.AUTO_APPROVE,
            }
            gate_config = GateConfig(
                id=stage.id,
                name=stage.name,
                description=stage.description,
                timeout_minutes=stage.timeout_minutes,
                timeout_policy=timeout_policy_map.get(stage.timeout_policy, TimeoutPolicy.REJECT),
                required_artifacts=stage.required_artifacts,
                freeze_artifacts=stage.freeze_artifacts,
            )
            return Node(
                id=stage.id,
                type=node_type,
                priority=priority,
                gate_config=gate_config,
            )
        else:
            # Task node
            task_config = TaskConfig(
                agent=stage.agent,
                model=model,
                max_turns=stage.max_turns,
            )
            return Node(
                id=stage.id,
                type=node_type,
                priority=priority,
                task_config=task_config,
            )

    def _resolve_stage_model(
        self,
        stage: WorkflowStageConfig,
    ) -> str | None:
        """Resolve the model string for a stage.

        Args:
            stage: WorkflowStageConfig

        Returns:
            Resolved model string or None
        """
        return self.providers_config.default_model

    # Model Validation

    def validate_models(
        self,
        config: WorkflowConfigYaml,
    ) -> ModelValidationResult:
        """Validate all model references in a workflow before execution.

        Collects ALL issues at once (no fail-on-first). Checks per-stage
        resolved models and allowlist validity.

        All models must be exact strings in the allowlist (no aliases).

        Args:
            config: WorkflowConfigYaml instance

        Returns:
            ModelValidationResult with all issues found
        """
        result = ModelValidationResult()

        for stage in config.stages:
            if stage.type in ("gate", "hook", "sub_workflow"):
                # Gate, hook, and sub-workflow stages don't need a model
                continue

            resolved = self._resolve_stage_model(stage)

            if not resolved:
                result.issues.append(
                    ModelValidationIssue(
                        stage_id=stage.id,
                        severity=ModelIssueSeverity.ERROR,
                        message="Model resolved to None — no agent default "
                        "or fallback could provide a value",
                        model_input=self._describe_model_source(stage),
                    )
                )
                continue

            self._validate_single_model(
                resolved,
                stage.id,
                self._describe_model_source(stage),
                result,
            )

        return result

    def _validate_single_model(
        self,
        model_string: str,
        stage_id: str,
        context: str,
        result: ModelValidationResult,
    ) -> None:
        """Validate a resolved model string against the allowlist.

        Args:
            model_string: The resolved model string
            stage_id: Stage this model belongs to
            context: Human-readable description of where model came from
            result: Result to append issues to
        """
        if not model_string:
            result.issues.append(
                ModelValidationIssue(
                    stage_id=stage_id,
                    severity=ModelIssueSeverity.ERROR,
                    message=f"Empty model string (source: {context})",
                    model_input="",
                )
            )
            return

        if not self.providers_config.is_allowed_model(model_string):
            # Also check if the provider prefix is known
            if "/" in model_string:
                provider_name = model_string.split("/", 1)[0]
                if provider_name not in self.providers_config.providers:
                    result.issues.append(
                        ModelValidationIssue(
                            stage_id=stage_id,
                            severity=ModelIssueSeverity.ERROR,
                            message=f"Unknown provider '{provider_name}' in model '{model_string}' "
                            f"(source: {context}). Known providers: "
                            f"{sorted(self.providers_config.providers.keys())}",
                            model_input=model_string,
                        )
                    )
                    return

            result.issues.append(
                ModelValidationIssue(
                    stage_id=stage_id,
                    severity=ModelIssueSeverity.ERROR,
                    message=f"Model '{model_string}' is not in the models allowlist "
                    f"(source: {context}). Allowed models: "
                    f"{self.providers_config.models}",
                    model_input=model_string,
                )
            )
        else:
            result.issues.append(
                ModelValidationIssue(
                    stage_id=stage_id,
                    severity=ModelIssueSeverity.INFO,
                    message=f"Resolved to '{model_string}' (source: {context})",
                    model_input=model_string,
                    resolved_to=model_string,
                )
            )

    def _describe_model_source(
        self,
        stage: WorkflowStageConfig,
    ) -> str:
        """Return human-readable string describing where a stage's model comes from.

        Args:
            stage: WorkflowStageConfig

        Returns:
            Description string
        """
        return "default model fallback"

    # Block Expansion

    def _expand_blocks(
        self,
        stages: list[WorkflowStageConfig],
        loops: list[LoopConfig],
    ) -> tuple[list[WorkflowStageConfig], list[LoopConfig]]:
        """Expand block references into inline stages.

        Block references (stages with `use:` field) are replaced by the
        block's stages. Optionally a prefix can be applied to stage IDs.

        Args:
            stages: List of stages that may contain block references
            loops: List of loop constraints from the workflow

        Returns:
            Tuple of (expanded_stages, expanded_loops) with all blocks inlined

        Raises:
            WorkflowLoadError: If a block cannot be loaded or has invalid structure
        """
        expanded_stages: list[WorkflowStageConfig] = []
        expanded_loops = list(loops)  # Start with workflow-level loops

        for stage in stages:
            if stage.use:
                # This is a block reference - load and expand it
                try:
                    block = self.block_loader.load_block(stage.use)
                except BlockLoadError as e:
                    raise WorkflowLoadError(str(e)) from e

                prefix = stage.prefix

                # Expand block stages with optional prefix
                for block_stage in block.stages:
                    new_id = f"{prefix}{block_stage.id}" if prefix else block_stage.id

                    merged_vars = {**block.variables, **stage.prompt_vars}

                    expanded_stage = block_stage.model_copy(
                        update={
                            "id": new_id,
                            "prompt_vars": {**block_stage.prompt_vars, **merged_vars},
                        }
                    )
                    expanded_stages.append(expanded_stage)

                # Expand block loops with prefixed stage IDs
                for block_loop in block.loops:
                    new_from = f"{prefix}{block_loop.from_}" if prefix else block_loop.from_
                    new_to = f"{prefix}{block_loop.to}" if prefix else block_loop.to
                    new_loop_id = f"{prefix}{block_loop.id}" if prefix else block_loop.id

                    expanded_loop = LoopConfig(  # type: ignore[call-arg]
                        id=new_loop_id,
                        from_=new_from,
                        to=new_to,
                        trigger=block_loop.trigger,
                        max_iterations=block_loop.max_iterations,
                        condition=block_loop.condition,
                    )
                    expanded_loops.append(expanded_loop)
            else:
                # Regular inline stage - keep as-is
                expanded_stages.append(stage)

        # This must happen after all blocks are expanded so we have the full stage list
        expanded_loops = self._resolve_loop_references(expanded_stages, expanded_loops)

        return expanded_stages, expanded_loops

    def _resolve_loop_references(
        self,
        stages: list[WorkflowStageConfig],
        loops: list[LoopConfig],
    ) -> list[LoopConfig]:
        """Resolve block reference tokens in loop targets.

        Tokens like {implement}, {prev_block}, {write_test}, {gate} are resolved
        to actual stage IDs based on the expanded stage list.

        Args:
            stages: Fully expanded list of stages
            loops: Loop constraints that may contain reference tokens

        Returns:
            List of loops with resolved targets
        """
        resolved_loops = []
        stage_ids = [s.id for s in stages]

        for loop in loops:
            to_target = loop.to
            if to_target.startswith("{") and to_target.endswith("}"):
                token = to_target[1:-1]  # Strip braces

                resolved_id = self._resolve_reference_token(token, loop.from_, stages, stage_ids)

                if resolved_id:
                    resolved_loops.append(loop.model_copy(update={"to": resolved_id}))
                else:
                    # Token couldn't be resolved - skip this loop with a warning
                    import warnings

                    warnings.warn(
                        f"Loop '{loop.id}' has unresolvable target token '{to_target}'. "
                        f"Loop will be ignored.",
                        UserWarning,
                        stacklevel=2,
                    )
            else:
                # Not a reference token - keep as-is
                resolved_loops.append(loop)

        return resolved_loops

    def _resolve_reference_token(
        self,
        token: str,
        from_node: str,
        stages: list[WorkflowStageConfig],
        stage_ids: list[str],
    ) -> str | None:
        """Resolve a block reference token to an actual stage ID.

        Supported tokens:
        - {implement}: Nearest stage with agent implementer/frontend-implementer
        - {write_test}: Nearest stage with agent test-writer
        - {prev_block}: Last stage of the previous block
        - {gate}: Nearest preceding gate stage
        - {stage_id}: Explicit exit_point marker on a stage

        Args:
            token: Token name without braces (e.g., "implement")
            from_node: Source stage ID where the loop originates
            stages: List of all stages
            stage_ids: List of stage IDs in execution order

        Returns:
            Resolved stage ID or None if not found
        """
        try:
            from_idx = stage_ids.index(from_node)
        except ValueError:
            return None

        # Check for explicit exit_point marker first
        for stage in stages:
            if stage.exit_point == token:
                return stage.id

        # Token-specific resolution logic
        if token == "implement":
            for i in range(from_idx - 1, -1, -1):
                stage = stages[i]
                if stage.agent in ["implementer", "frontend-implementer"]:
                    return stage.id

        elif token == "write_test":
            for i in range(from_idx - 1, -1, -1):
                stage = stages[i]
                if stage.agent == "test-writer":
                    return stage.id

        elif token == "prev_block":
            # A "block" ends when we hit a gate or the sequence of same-prefix stages ends
            for i in range(from_idx - 1, -1, -1):
                stage = stages[i]
                if stage.type == "gate":
                    if i + 1 < len(stages):
                        return stages[i + 1].id
                    return None
                # Check for block boundary (prefix change)
                current_prefix = stage.id.split("-")[0] if "-" in stage.id else stage.id
                if i > 0:
                    next_stage = stages[i - 1]
                    next_prefix = (
                        next_stage.id.split("-")[0] if "-" in next_stage.id else next_stage.id
                    )
                    # If prefix changes, we found a block boundary
                    if current_prefix != next_prefix:
                        return stage.id
                else:
                    # First stage - return it
                    return stage.id
            # Fallback: return immediate predecessor
            if from_idx > 0:
                return stage_ids[from_idx - 1]

        elif token == "gate":
            for i in range(from_idx - 1, -1, -1):
                stage = stages[i]
                if stage.type == "gate":
                    return stage.id

        # Token not resolved
        return None

def load_workflow_from_yaml(project_path: Path, workflow_id: str | Path) -> WorkflowTemplate:
    """Load a workflow template from YAML.

    Convenience function that creates a loader and returns a template.

    Args:
        project_path: Path to the project root
        workflow_id: Workflow ID or path to YAML file

    Returns:
        WorkflowTemplate instance

    Raises:
        WorkflowLoadError: If workflow not found or invalid
    """
    loader = WorkflowLoader(project_path)
    config = loader.load_workflow(workflow_id)
    return loader.convert_to_template(config)

def list_yaml_workflows(project_path: Path) -> list[dict[str, Any]]:
    """List all available YAML workflows.

    Convenience function that creates a loader and returns workflows.

    Args:
        project_path: Path to the project root

    Returns:
        List of workflow metadata dictionaries
    """
    loader = WorkflowLoader(project_path)
    return loader.list_workflows()

__all__ = [
    "BlockLoadError",
    "ModelIssueSeverity",
    "ModelValidationIssue",
    "ModelValidationResult",
    "WorkflowLoadError",
    "WorkflowLoader",
    "load_workflow_from_yaml",
    "list_yaml_workflows",
]
