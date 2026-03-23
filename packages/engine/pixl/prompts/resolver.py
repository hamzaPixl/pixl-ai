"""Prompt template resolver for YAML workflows.

This module provides functionality for:
1. Loading shared prompt templates from ~/.pixl/prompts/ and .pixl/prompts/
2. Resolving prompt references (prompt_ref)
3. Substituting variables in prompt templates
"""

import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pixl.paths import get_global_pixl_dir, get_prompts_dir

logger = logging.getLogger("pixl.prompts")

# Default variable values available to all workflows
DEFAULT_VARIABLES = {
    "project_root": ".",  # Will be set at runtime
    "pixl_dir": ".pixl",
    "artifacts_dir": "{pixl_dir}/sessions/{session_id}/artifacts",
    "pixl_version": "1.0.0",
}


class PromptContext(BaseModel):
    """Context for prompt template rendering."""

    workflow_id: str
    workflow_name: str
    feature_id: str
    feature_title: str
    feature_description: str
    session_id: str
    stage_id: str
    project_root: Path
    artifacts_dir: Path
    pixl_dir: Path

    def to_dict(self) -> dict[str, str]:
        """Convert context to dictionary for template substitution."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "feature_id": self.feature_id,
            "title": self.feature_title,
            "description": self.feature_description,
            "session_id": self.session_id,
            "stage_id": self.stage_id,
            "project_root": str(self.project_root),
            "artifacts_dir": str(self.artifacts_dir),
            "pixl_dir": str(self.pixl_dir),
        }


class PromptTemplateResolver:
    """Resolves and renders prompt templates for workflow stages.

    Resolution order:
    1. Inline prompt from stage.prompt
    2. Referenced template from stage.prompt_ref (project → global → bundled)
    3. Fallback to generic prompt
    """

    # Bundled prompts shipped with the pixl package
    BUNDLED_PROMPTS_DIR = Path(__file__).parent.parent / "assets" / "prompts"

    def __init__(
        self,
        project_root: Path,
        global_prompts_dir: Path | None = None,
        bundled_prompts_dir: Path | None = None,
    ):
        """Initialize the resolver.

        Args:
            project_root: Project root directory
            global_prompts_dir: Global prompts directory (defaults to ~/.pixl/prompts/)
            bundled_prompts_dir: Bundled prompts directory (defaults to package assets)
        """
        self.project_root = project_root
        self.global_prompts_dir = global_prompts_dir or (get_global_pixl_dir() / "prompts")
        self.local_prompts_dir = get_prompts_dir(project_root)
        self.bundled_prompts_dir = bundled_prompts_dir or self.BUNDLED_PROMPTS_DIR

        # Cache for loaded templates
        self._template_cache: dict[str, str] = {}

    def resolve_stage_prompt(
        self,
        stage_config: Any,  # WorkflowStageConfig or dict
        context: PromptContext,
        global_vars: dict[str, str] | None = None,
        parameters: dict[str, str] | None = None,
    ) -> str:
        """Resolve the prompt for a workflow stage.

        Args:
            stage_config: Stage configuration from YAML (can be dict or object)
            context: Prompt rendering context
            global_vars: Additional global variables from workflow YAML
            parameters: User-provided parameters from workflow definition

        Returns:
            Resolved prompt string
        """
        if isinstance(stage_config, dict):
            prompt = stage_config.get("prompt")
            prompt_ref = stage_config.get("prompt_ref")
            prompt_vars = stage_config.get("prompt_vars", {})
        else:
            prompt = stage_config.prompt
            prompt_ref = stage_config.prompt_ref
            prompt_vars = stage_config.prompt_vars if stage_config.prompt_vars else {}

        if prompt:
            # Inline prompt takes precedence
            template = prompt
        elif prompt_ref:
            template = self._load_template(prompt_ref)
            if not template:
                template = self._get_fallback_prompt(stage_config)
        else:
            # Use fallback generic prompt
            template = self._get_fallback_prompt(stage_config)

        variables = self._build_variables(
            context=context,
            global_vars=global_vars or {},
            stage_vars=prompt_vars,
            parameters=parameters,
        )

        # Substitute variables
        result = self._substitute_variables(template, variables)

        # Warn if critical variables were referenced in the template but resolved to empty
        critical_vars = ("description", "title", "feature_id")
        for var_name in critical_vars:
            if f"{{{var_name}}}" in template or f"{{{{{var_name}}}}}" in template:
                value = variables.get(var_name, "")
                if not value:
                    logger.warning(
                        "Prompt template for stage '%s' references {%s} but it resolved to empty. "
                        "This may indicate missing feature data.",
                        context.stage_id,
                        var_name,
                    )

        return result

    def _load_template(self, ref: str) -> str | None:
        """Load a prompt template by reference.

        Resolution order: project → global → bundled

        Args:
            ref: Template reference (e.g., 'stages/brainstorm')

        Returns:
            Template content or None if not found
        """
        # Check cache first
        if ref in self._template_cache:
            return self._template_cache[ref]

        # ref can be:
        # - 'template-name' -> template.yaml
        # - 'category/template-name' -> category/template-name.yaml
        # - 'template-name.yaml' -> direct file reference
        # - '/absolute/path/to/template.yaml' -> absolute path

        ref_clean = ref.strip()
        if ref_clean.endswith(".yaml") or ref_clean.endswith(".yml"):
            ref_base = ref_clean.rsplit(".", 1)[0]
        else:
            ref_base = ref_clean

        # Try local prompts first (project-specific, highest priority)
        local_path = self.local_prompts_dir / f"{ref_base}.yaml"
        if local_path.exists():
            content = local_path.read_text(encoding="utf-8")
            self._template_cache[ref] = content
            return content

        # Try global prompts (user's shared library)
        global_path = self.global_prompts_dir / f"{ref_base}.yaml"
        if global_path.exists():
            content = global_path.read_text(encoding="utf-8")
            self._template_cache[ref] = content
            return content

        # Try bundled prompts (lowest priority)
        bundled_path = self.bundled_prompts_dir / f"{ref_base}.yaml"
        if bundled_path.exists():
            content = bundled_path.read_text(encoding="utf-8")
            self._template_cache[ref] = content
            return content

        # Try as category/template in global prompts
        if "/" not in ref_clean:
            # Try common categories
            for category in ["common", "tasks", "gates", "validation", "stages"]:
                # Check global
                cat_path = self.global_prompts_dir / category / f"{ref_base}.yaml"
                if cat_path.exists():
                    content = cat_path.read_text(encoding="utf-8")
                    self._template_cache[ref] = content
                    return content
                # Check bundled
                bundled_cat_path = self.bundled_prompts_dir / category / f"{ref_base}.yaml"
                if bundled_cat_path.exists():
                    content = bundled_cat_path.read_text(encoding="utf-8")
                    self._template_cache[ref] = content
                    return content

        return None

    def _build_variables(
        self,
        context: PromptContext,
        global_vars: dict[str, str],
        stage_vars: dict[str, str],
        parameters: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Build complete variables dictionary for substitution.

        Priority (highest to lowest):
        1. Stage variables (stage_vars)
        2. Parameters (user-provided, from interactive collection)
        3. Workflow global variables (global_vars)
        4. Context variables (context)
        5. Default variables

        Args:
            context: Prompt rendering context
            global_vars: Global variables from workflow YAML
            stage_vars: Stage-specific prompt variables
            parameters: User-provided parameters (from workflow definition)

        Returns:
            Complete variables dictionary
        """
        variables: dict[str, str] = {}

        variables.update(DEFAULT_VARIABLES)

        variables.update(context.to_dict())

        variables.update({str(k): str(v) for k, v in global_vars.items()})

        if parameters:
            variables.update({str(k): str(v) for k, v in parameters.items()})

        variables.update({str(k): str(v) for k, v in stage_vars.items()})

        if variables.get("project_root") == ".":
            variables["project_root"] = str(context.project_root)

        # Resolve nested variables (e.g., plan_file uses {feature_id}, artifacts_dir, etc.)
        variables = self._resolve_nested_variables(variables)

        return variables

    def _resolve_nested_variables(self, variables: dict[str, str]) -> dict[str, str]:
        """Resolve nested {var} and {{var}} references in variable values."""
        resolved = {str(k): str(v) for k, v in variables.items()}
        for _ in range(3):
            prev = dict(resolved)
            for key, value in resolved.items():
                resolved[key] = self._substitute_variables(value, resolved)
            if resolved == prev:
                break
        return resolved

    def _substitute_variables(self, template: str, variables: dict[str, str]) -> str:
        """Substitute variables in template string.

        Supports:
        - {var_name} - Simple substitution
        - {var_name|default} - Substitution with default value
        - {{var_name}} - Double-brace substitution
        - {{var_name|default}} - Double-brace substitution with default

        Args:
            template: Template string with variable placeholders
            variables: Variables dictionary

        Returns:
            Rendered template
        """
        # Pattern for {var|default} or {var}
        single_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)(\|([^{}]*))?\}"
        double_pattern = r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)(\|([^{}]*))?\}\}"

        def _replace(match: re.Match[str], var_group: int, default_group: int) -> str:
            var_name = match.group(var_group)
            default_value = match.group(default_group) if match.group(default_group) else ""
            value = variables.get(var_name)
            if value is not None and value != "":
                return str(value)
            return default_value

        result = re.sub(double_pattern, lambda m: _replace(m, 1, 3), template)
        result = re.sub(single_pattern, lambda m: _replace(m, 1, 3), result)

        return result

    def _get_fallback_prompt(self, stage_config: Any) -> str:
        """Get fallback generic prompt for a stage.

        Args:
            stage_config: Stage configuration

        Returns:
            Generic prompt string
        """
        outputs: list[str] = []
        if isinstance(stage_config, dict):
            outputs = stage_config.get("outputs") or []
        else:
            outputs = getattr(stage_config, "outputs", []) or []

        outputs_section = ""
        if outputs:
            formatted = "\n".join(f"- {o}" for o in outputs)
            outputs_section = f"""
## Expected Artifacts

Use `pixl artifact put` to save non-code artifacts (returns SHA256 hash;
use `--json` for machine-readable output).
Use `pixl artifact get` to read artifacts by logical session path.
Use `pixl artifact get --json` for machine-readable reads
(`name`, `session_id`, `sha256`, `content`).
Use `pixl artifact list` to list session artifacts and versions.
Use `pixl artifact search` for full-text search over session artifacts.

Use these commands INSTEAD of writing directly to `{{artifacts_dir}}`.
If a file path below is relative, treat it as relative to the artifacts directory.

{formatted}
"""

        return f"""You are executing workflow stage: {{stage_id}}

## Feature: {{feature_id}} - {{title}}

{{description}}

## Your Task

Complete the workflow stage: {{stage_id}}
{outputs_section}

Use the available tools:
- Read files (Read, Glob, Grep)
- Write/Edit files (Write, Edit)
- Run commands (Bash)
- Create tests and implementation

Focus on quality and correctness. Follow existing patterns in the codebase.
"""

    def list_available_templates(self) -> list[dict[str, str]]:
        """List all available prompt templates.

        Returns:
            List of template info dicts with 'name', 'source', 'path'.
            Higher-priority sources (project > global > bundled) override lower ones.
        """
        # Use a dict to track seen names, with higher priority sources winning
        seen_names: dict[str, dict[str, str]] = {}

        # Helper to add templates from a directory
        def add_from_dir(prompts_dir: Path, source: str) -> None:
            if not prompts_dir.exists():
                return
            for yaml_file in prompts_dir.rglob("*.yaml"):
                rel_path = yaml_file.relative_to(prompts_dir)
                name = str(rel_path.with_suffix(""))
                # Only add if not already seen (higher priority wins)
                if name not in seen_names:
                    seen_names[name] = {
                        "name": name,
                        "source": source,
                        "path": str(yaml_file),
                    }

        # Scan in precedence order: project → global → bundled
        # (First source wins for duplicate names)
        add_from_dir(self.local_prompts_dir, "project")
        add_from_dir(self.global_prompts_dir, "global")
        add_from_dir(self.bundled_prompts_dir, "bundled")

        return sorted(seen_names.values(), key=lambda t: (t["source"], t["name"]))


__all__ = [
    "PromptContext",
    "PromptTemplateResolver",
]
