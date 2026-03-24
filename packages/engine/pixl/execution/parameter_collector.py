"""Generic parameter collector from workflow YAML.

Collects parameters interactively based on workflow definition,
keeping all prompts declarative in YAML.
"""

from typing import Any

from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from pixl.models.workflow_config import ParameterConfig, WorkflowConfigYaml
from pixl.output import console


class WorkflowParameterCollector:
    """Collects parameters interactively based on workflow YAML definition."""

    def __init__(
        self,
        workflow_config: WorkflowConfigYaml | dict,
        context: dict[str, Any] | None = None,
    ):
        """Initialize the parameter collector.

        Args:
            workflow_config: Workflow configuration (model or dict)
            context: Initial context for default value substitution
        """
        if isinstance(workflow_config, dict):
            self.config = WorkflowConfigYaml.model_validate(workflow_config)
        else:
            self.config = workflow_config
        self.context = context or {}

    @property
    def parameters(self) -> list[ParameterConfig]:
        """Get parameter definitions from workflow config."""
        return self.config.parameters

    def collect(
        self,
        interactive: bool = True,
        show_advanced: bool = False,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Collect all parameters.

        Args:
            interactive: If True, prompt user. If False, use defaults.
            show_advanced: If True, show advanced parameters.
            overrides: Pre-provided values (skip prompting for these).

        Returns:
            Dict of parameter_id -> value
        """
        overrides = overrides or {}
        values = {}

        if not self.parameters:
            return {**self.config.variables, **overrides}

        if interactive:
            self._show_header()

        basic_params = [p for p in self.parameters if not p.advanced]
        for param in basic_params:
            if param.id in overrides:
                values[param.id] = overrides[param.id]
                if interactive:
                    self._show_override(param, overrides[param.id])
            elif interactive:
                values[param.id] = self._prompt_parameter(param, values)
            else:
                values[param.id] = self._resolve_default(param, values)

        # Ask about advanced options
        advanced_params = [p for p in self.parameters if p.advanced]
        if interactive and not show_advanced and advanced_params:
            console._console.print()
            show_advanced = Confirm.ask(
                "[dim]Configure advanced options?[/dim]",
                default=False,
                console=console._console,
            )

        if show_advanced and advanced_params:
            console._console.print()
            console.print("[bold]Advanced Options[/bold]")
            for param in advanced_params:
                if param.id in overrides:
                    values[param.id] = overrides[param.id]
                elif interactive:
                    values[param.id] = self._prompt_parameter(param, values)
                else:
                    values[param.id] = self._resolve_default(param, values)
        else:
            # Use defaults for advanced params
            for param in advanced_params:
                if param.id in overrides:
                    values[param.id] = overrides[param.id]
                else:
                    values[param.id] = self._resolve_default(param, values)

        if interactive:
            self._show_summary(values)
            console._console.print()
            if not Confirm.ask("[bold]Proceed?[/bold]", default=True, console=console._console):
                raise SystemExit(0)

        return {**self.config.variables, **values}

    def _show_header(self) -> None:
        """Show workflow header."""
        console._console.print()
        console._console.print(
            Panel(
                f"[bold]{self.config.name}[/bold]\n\n{self.config.description or 'No description'}",
                title="Workflow Setup",
                border_style="cyan",
            )
        )
        console._console.print()

    def _resolve_default(self, param: ParameterConfig, current_values: dict[str, Any]) -> Any:
        """Resolve default value, substituting context variables.

        Substitution syntax (matches prompt resolver):
        - {{var_name}} - Variable substitution
        - {{{{var_name}}}} - Escaped literal braces (outputs {var_name})
        """
        default = param.default

        if default is None:
            if param.type == "confirm":
                return False
            elif param.type == "checklist":
                if param.options:
                    result = {}
                    for opt in param.options:
                        if isinstance(opt, dict):
                            result[opt.get("id", "")] = opt.get("default", False)
                        elif hasattr(opt, "id"):
                            result[opt.id] = opt.default  # type: ignore[union-attr]
                        else:
                            result[str(opt)] = False
                    return result
                return {}
            return None

        if isinstance(default, str) and "{" in default:
            # Template substitution from context and already-collected values
            # Uses {{var}} syntax to match prompt resolver semantics
            merged = {**self.context, **current_values}
            for key, value in merged.items():
                # {{var}} syntax for substitution (double braces)
                default = default.replace(f"{{{{{key}}}}}", str(value))

        return default

    def _show_override(self, param: ParameterConfig, value: Any) -> None:
        """Show that a parameter was provided via override."""
        display = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        console.info(f"{param.label}: [cyan]{display}[/cyan]")

    def _prompt_parameter(self, param: ParameterConfig, current_values: dict[str, Any]) -> Any:
        """Prompt for a single parameter based on its type."""
        default = self._resolve_default(param, current_values)

        if param.description:
            console.print(f"[dim]{param.description}[/dim]")

        if param.type == "string":
            result = Prompt.ask(
                f"[bold]{param.label}[/bold]",
                default=default if default else None,
                console=console._console,
            )
            return result

        elif param.type == "text":
            console.print(f"[bold]{param.label}[/bold]")
            result = Prompt.ask(
                "",
                default=default if default else None,
                console=console._console,
            )
            return result

        elif param.type == "confirm":
            result = Confirm.ask(
                f"[bold]{param.label}[/bold]",
                default=default if isinstance(default, bool) else False,
                console=console._console,
            )
            return result

        elif param.type == "choice":
            choices = []
            if param.options:
                for opt in param.options:
                    if isinstance(opt, str):
                        choices.append(opt)
                    elif isinstance(opt, dict):
                        choices.append(opt.get("id", str(opt)))
                    elif hasattr(opt, "id"):
                        choices.append(opt.id)

            result = Prompt.ask(
                f"[bold]{param.label}[/bold]",
                choices=choices if choices else None,
                default=default if default else None,
                console=console._console,
            )
            return result

        elif param.type == "checklist":
            console.print(f"[bold]{param.label}[/bold]")
            result = {}

            if param.options:
                for opt in param.options:
                    if isinstance(opt, str):
                        opt_id = opt
                        opt_label = opt
                        opt_default = False
                    elif isinstance(opt, dict):
                        opt_id = opt.get("id", "")
                        opt_label = opt.get("label", opt_id)
                        opt_default = opt.get("default", False)
                    else:
                        opt_id = opt.id
                        opt_label = opt.label
                        opt_default = opt.default

                    result[opt_id] = Confirm.ask(
                        f"  {opt_label}",
                        default=opt_default,
                        console=console._console,
                    )

            return result

        return default

    def _show_summary(self, values: dict[str, Any]) -> None:
        """Show summary of collected values."""
        console._console.print()

        table = Table(title="Summary", border_style="cyan")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")

        for param in self.parameters:
            value = values.get(param.id)
            if isinstance(value, dict):
                # Checklist - show enabled items
                enabled = [k for k, v in value.items() if v]
                display = ", ".join(enabled) if enabled else "(none)"
            elif isinstance(value, bool):
                display = "[green]Yes[/green]" if value else "[red]No[/red]"
            elif value is None:
                display = "[dim](not set)[/dim]"
            else:
                display = str(value)[:40]
                if len(str(value)) > 40:
                    display += "..."

            table.add_row(param.label, display)

        console._console.print(table)


def collect_workflow_parameters(
    workflow_config: WorkflowConfigYaml | dict,
    context: dict[str, Any] | None = None,
    interactive: bool = True,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience function to collect workflow parameters.

    Args:
        workflow_config: Workflow configuration
        context: Initial context for substitution
        interactive: Whether to prompt interactively
        overrides: Pre-provided values

    Returns:
        Collected parameter values
    """
    collector = WorkflowParameterCollector(workflow_config, context)
    return collector.collect(interactive=interactive, overrides=overrides)
