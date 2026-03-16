"""Console output formatting with rich."""

from typing import Any

from rich.console import Console as RichConsole
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

from pixl.models.feature import Feature, FeatureStatus, Priority


class Console:
    """Formatted console output for pixl CLI."""

    def __init__(self) -> None:
        self._console = RichConsole()
        self._verbose = False

    def set_verbose(self, verbose: bool) -> None:
        """Enable or disable verbose/debug output."""
        self._verbose = verbose

    @property
    def verbose(self) -> bool:
        """Check if verbose mode is enabled."""
        return self._verbose

    # Basic output methods

    def print(self, message: str, style: str | None = None) -> None:
        """Print a message."""
        self._console.print(message, style=style)

    def print_json(self, json_str: str) -> None:
        """Print JSON using rich's pretty printer."""
        self._console.print_json(json_str)

    def info(self, message: str) -> None:
        """Print an info message."""
        self._console.print(f"[blue]i[/blue] {message}")

    def success(self, message: str) -> None:
        """Print a success message."""
        self._console.print(f"[green]✓[/green] {message}")

    def warning(self, message: str) -> None:
        """Print a warning message."""
        self._console.print(f"[yellow]![/yellow] {message}")

    def warn(self, message: str) -> None:
        """Alias for warning."""
        self.warning(message)

    def error(self, message: str) -> None:
        """Print an error message."""
        self._console.print(f"[red]✗[/red] {message}")

    def meta(self, message: str) -> None:
        """Print metadata (dimmed)."""
        self._console.print(f"[dim]{message}[/dim]")

    def debug(self, message: str) -> None:
        """Print debug message (only if verbose mode enabled)."""
        if self._verbose:
            self._console.print(f"[dim magenta]⚙[/dim magenta] [dim]{message}[/dim]")

    # Workflow stage display

    def stage(self, number: int, name: str, model: str) -> None:
        """Print workflow stage header."""
        self._console.print()
        self._console.print(
            Panel(
                f"[bold cyan]Stage {number}[/bold cyan]: [bold white]{name}[/bold white]\n"
                f"[dim]Provider: {model}[/dim]",
                border_style="cyan",
                padding=(0, 2),
            )
        )

    def stage_extra(self, name: str, model: str) -> None:
        """Print extra workflow stage (not numbered)."""
        self._console.print()
        self._console.print(
            Panel(
                f"[bold magenta]{name}[/bold magenta]\n[dim]Provider: {model}[/dim]",
                border_style="magenta",
                padding=(0, 2),
            )
        )

    def agent(self, name: str, model: str) -> None:
        """Print agent activation message."""
        self._console.print(f"[cyan]▶[/cyan] [bold cyan]{name}[/bold cyan] [dim]({model})[/dim]")

    def hook(self, event: str, hooks: list[str]) -> None:
        """Print hook execution message."""
        if hooks:
            hooks_str = ", ".join(hooks)
            self._console.print(f"[dim magenta]⚡[/dim magenta] [dim]{event}: {hooks_str}[/dim]")

    def model_resolved(self, alias: str, resolved: str) -> None:
        """Print model resolution message (only if verbose)."""
        if self._verbose:
            self._console.print(
                f"[dim magenta]⚙[/dim magenta] [dim]Model: {alias} → {resolved}[/dim]"
            )

    def skill_loaded(self, skill_name: str) -> None:
        """Print skill loaded message (only if verbose)."""
        if self._verbose:
            self._console.print(f"[dim magenta]📚[/dim magenta] [dim]Skill: {skill_name}[/dim]")

    def hooks_registered(self, hooks: list[str]) -> None:
        """Print registered hooks at startup."""
        if hooks:
            hooks_str = ", ".join(hooks)
            self._console.print(f"[dim]⚡ Hooks: {hooks_str}[/dim]")

    def tools_allowed(self, tools: list[str]) -> None:
        """Print allowed tools for this operation."""
        if tools:
            tools_str = ", ".join(tools)
            self._console.print(f"[dim]🔧 Tools: {tools_str}[/dim]")

    def status(self, message: str) -> None:
        """Print status line (overwrites previous line)."""
        # Use carriage return to overwrite the line
        self._console.print(f"\r[cyan]{message}[/cyan]", end="")

    # Streaming display methods for real-time SDK output

    def stream_tool_call(self, tool_name: str, tool_input: dict) -> None:
        """Display a tool call in real-time."""
        if tool_name == "Read":
            path = tool_input.get("file_path", "")
            self._console.print(f"  [dim cyan]Read[/dim cyan] [dim]{path}[/dim]")
        elif tool_name == "Write":
            path = tool_input.get("file_path", "")
            self._console.print(f"  [dim green]Write[/dim green] [dim]{path}[/dim]")
        elif tool_name == "Edit":
            path = tool_input.get("file_path", "")
            self._console.print(f"  [dim yellow]Edit[/dim yellow] [dim]{path}[/dim]")
        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")[:80]
            self._console.print(f"  [dim magenta]Bash[/dim magenta] [dim]{cmd}[/dim]")
        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            self._console.print(f"  [dim]Glob[/dim] [dim]{pattern}[/dim]")
        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            self._console.print(f"  [dim]Grep[/dim] [dim]{pattern}[/dim]")
        elif tool_name == "Task":
            desc = tool_input.get("description", "")
            self._console.print(f"  [dim blue]Task[/dim blue] [dim]{desc}[/dim]")
        elif tool_name == "WebSearch":
            q = tool_input.get("query", "")
            self._console.print(f"  [dim]WebSearch[/dim] [dim]{q}[/dim]")
        elif tool_name == "WebFetch":
            url = tool_input.get("url", "")
            self._console.print(f"  [dim]WebFetch[/dim] [dim]{url}[/dim]")
        else:
            self._console.print(f"  [dim]{tool_name}[/dim]")

    def stream_thinking(self, content: str) -> None:
        """Display thinking/reasoning content.

        Always shows a summary; verbose mode shows extended content.
        """
        if self._verbose:
            text = content[:500] + "..." if len(content) > 500 else content
        else:
            text = content[:200] + "..." if len(content) > 200 else content
        if text.strip():
            self._console.print(f"  [dim magenta]thinking:[/dim magenta] [dim]{text}[/dim]")

    def stream_text(self, content: str) -> None:
        """Display assistant text output (abbreviated)."""
        text = content[:200] + "..." if len(content) > 200 else content
        if text.strip():
            self._console.print(f"  [dim]{text}[/dim]")

    def markdown(self, content: str) -> None:
        """Print markdown content."""
        self._console.print(Markdown(content))

    # Feature display methods

    def _priority_style(self, priority: Priority) -> str:
        """Get style for priority."""
        return {
            Priority.P0: "bold red",
            Priority.P1: "bold yellow",
            Priority.P2: "blue",
            Priority.P3: "dim",
        }.get(priority, "")

    def _status_style(self, status: FeatureStatus) -> str:
        """Get style for status."""
        return {
            FeatureStatus.BACKLOG: "dim",
            FeatureStatus.PLANNED: "cyan",
            FeatureStatus.IN_PROGRESS: "yellow",
            FeatureStatus.REVIEW: "magenta",
            FeatureStatus.BLOCKED: "red",
            FeatureStatus.DONE: "green",
            FeatureStatus.FAILED: "red dim",
        }.get(status, "")

    def feature_row(self, feature: Feature) -> None:
        """Print a single feature as a row."""
        priority_style = self._priority_style(feature.priority)
        status_style = self._status_style(feature.status)

        self._console.print(
            f"[dim]{feature.id}[/dim] "
            f"[{priority_style}]{feature.priority.value}[/{priority_style}] "
            f"[{status_style}]{feature.status.value:12}[/{status_style}] "
            f"{feature.title}"
        )

    def feature_table(self, features: list[Feature], title: str = "Features") -> None:
        """Print features as a table."""
        if not features:
            self.info("No features found")
            return

        table = Table(title=title, show_header=True, header_style="bold")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Priority", width=4)
        table.add_column("Status", width=12)
        table.add_column("Type", width=8)
        table.add_column("Title")

        for f in features:
            priority_style = self._priority_style(f.priority)
            status_style = self._status_style(f.status)

            table.add_row(
                f.id,
                Text(f.priority.value, style=priority_style),
                Text(f.status.value, style=status_style),
                f.type.value,
                f.title,
            )

        self._console.print(table)

    def feature_detail(self, feature: Feature) -> None:
        """Print detailed feature information."""
        priority_style = self._priority_style(feature.priority)
        status_style = self._status_style(feature.status)

        content = [
            f"[bold]{feature.title}[/bold]",
            "",
            f"[dim]ID:[/dim]       {feature.id}",
            f"[dim]Type:[/dim]     {feature.type.value}",
            f"[dim]Priority:[/dim] [{priority_style}]{feature.priority.value}[/{priority_style}]",
            f"[dim]Status:[/dim]   [{status_style}]{feature.status.value}[/{status_style}]",
        ]

        if feature.description:
            content.extend(["", "[dim]Description:[/dim]", feature.description])

        if feature.depends_on:
            content.extend(["", "[dim]Depends on:[/dim] " + ", ".join(feature.depends_on)])

        if feature.blocked_by:
            content.extend(["", f"[red]Blocked by:[/red] {feature.blocked_by}"])
            if feature.blocked_reason:
                content.append(f"[red]Reason:[/red] {feature.blocked_reason}")

        if feature.plan_path:
            content.extend(["", f"[dim]Plan:[/dim] {feature.plan_path}"])

        if feature.pr_url:
            content.extend(["", f"[dim]PR:[/dim] {feature.pr_url}"])

        if feature.total_cost_usd > 0:
            content.extend(
                [
                    "",
                    "[dim]Metrics:[/dim]",
                    f"  Cost:   ${feature.total_cost_usd:.4f}",
                    f"  Tokens: {feature.total_tokens:,}",
                ]
            )

        if feature.notes:
            content.extend(["", "[dim]Notes:[/dim]"])
            for note in feature.notes[-5:]:  # Show last 5 notes
                content.append(f"  {note}")

        self._console.print(Panel("\n".join(content), border_style="blue"))

    # Stats display

    def stats(self, stats: dict[str, int]) -> None:
        """Print backlog statistics."""
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        for key, value in stats.items():
            style = ""
            if key == "in_progress":
                style = "yellow"
            elif key == "done":
                style = "green"
            elif key == "blocked":
                style = "red"

            table.add_row(key.replace("_", " ").title(), Text(str(value), style=style))

        self._console.print(table)

    # Progress display

    def progress(self, description: str = "Working...") -> Progress:
        """Create a progress context."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console,
        )

    def spinner(self, message: str) -> Any:
        """Create a spinner context."""
        return self._console.status(message, spinner="dots")

    # Cost display

    def cost_warning(self, cost: float, threshold: float) -> None:
        """Display cost warning if threshold exceeded."""
        if cost >= threshold:
            self._console.print(
                Panel(
                    f"[yellow]Cost warning: ${cost:.4f} (threshold: ${threshold:.4f})[/yellow]",
                    border_style="yellow",
                )
            )

    def cost_summary(self, cost: float, tokens: int) -> None:
        """Print cost summary."""
        self._console.print(f"[dim]Cost: ${cost:.4f} | Tokens: {tokens:,}[/dim]")


# Global console instance
console = Console()
