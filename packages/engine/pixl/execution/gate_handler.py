"""Interactive gate handler for CLI workflow execution.

Provides interactive prompts for gate approval with artifact viewing,
validation, and user decision handling.
"""

import fnmatch
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pixl.models.workflow import GateConfig, Node
from pixl.output import console

# Safe pattern for artifact references - prevent path traversal
# Allows: *.md, *.txt, **/*.md, filename.md, dir/*.md
# Rejects: ../, ..\\, /etc/, ~/, etc.
SAFE_ARTIFACT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-./**]+$")

def validate_artifact_pattern(pattern: str, project_root: Path) -> bool:
    """Validate an artifact pattern is safe and within project bounds.

    Args:
        pattern: Artifact pattern to validate
        project_root: Project root directory

    Returns:
        True if pattern is safe, False otherwise
    """
    # Reject empty patterns
    if not pattern:
        return False

    # Check for obvious path traversal attempts
    if ".." in pattern or pattern.startswith("/") or pattern.startswith("~"):
        return False

    # Match against safe character set
    if not SAFE_ARTIFACT_PATTERN.match(pattern):
        return False

    # For glob patterns, verify they don't escape project root
    if "*" in pattern:
        prefix = pattern.split("*")[0].split("/")[0]
        if prefix == "..":
            return False

    try:
        resolved = (project_root / pattern).resolve()
        # Use relative_to which raises ValueError if not contained
        resolved.relative_to(project_root.resolve())
        return True
    except (ValueError, RuntimeError):
        # Path escapes project root
        return False

class InteractiveGateHandler:
    """Handles interactive gate approval in CLI.

    Provides a user-friendly interface for:
    - Viewing gate information
    - Checking required artifacts
    - Previewing artifact content
    - Approving/rejecting gates
    - Skipping gates (with warning)
    """

    def __init__(
        self,
        console_output: Any,  # ConsoleOutput - avoid circular import
        artifacts_dir: Path,
        store: Any,  # WorkflowSessionStore - avoid circular import
        project_root: Path | None = None,
    ):
        """Initialize the interactive gate handler.

        Args:
            console_output: ConsoleOutput instance for output
            artifacts_dir: Directory containing artifacts
            store: Session store for loading artifact content
            project_root: Project root directory (for finding artifacts in project)
        """
        self.console = console_output
        self.artifacts_dir = artifacts_dir
        self.store = store
        # Derive project root from artifacts_dir if not provided
        # artifacts_dir is typically: project/.pixl/sessions/sess-xxx/artifacts
        self.project_root = project_root or artifacts_dir.parent.parent.parent.parent
        self.last_rejection_reason: str | None = None

    def handle_gate(
        self,
        node: Node,
        session_id: str,
        node_instance: dict[str, Any] | None = None,
    ) -> bool:
        """Handle gate approval - returns True if approved.

        Args:
            node: Gate node to handle
            session_id: Current session ID
            node_instance: Optional node instance data for timeout checking

        Returns:
            True if gate approved, False if rejected
        """
        gate_config = node.gate_config
        if not gate_config:
            self.console.error(f"Node '{node.id}' has no gate configuration")
            return False

        # Check timeout before proceeding
        if gate_config.timeout_minutes and node_instance:
            timeout_result = self._check_gate_timeout(gate_config, node_instance, node.id)
            if timeout_result is not None:  # Timeout triggered
                return timeout_result

        self._show_gate_header(gate_config)

        missing_artifacts = self._show_required_artifacts(gate_config, session_id)

        if gate_config.timeout_minutes:
            self.console.info(
                f"Timeout: [dim]{gate_config.timeout_minutes} minutes "
                f"(policy: {gate_config.timeout_policy.value})[/dim]"
            )

        # If artifacts are missing, warn user
        if missing_artifacts:
            self.console.warn(
                f"\n⚠ Some required artifacts are missing: {', '.join(missing_artifacts)}"
            )
            self.console.info("You may want to wait or check the workflow before approving.")

        return self._get_user_approval(gate_config, session_id, node.id)

    def _check_gate_timeout(
        self,
        gate_config: GateConfig,
        node_instance: dict[str, Any],
        node_id: str,
    ) -> bool | None:
        """Check if gate has timed out and apply timeout policy.

        Args:
            gate_config: Gate configuration
            node_instance: Node instance data containing ready_at timestamp
            node_id: Gate node ID

        Returns:
            True (auto-approve), False (reject), or None (no timeout)
        """
        ready_at_str = node_instance.get("ready_at")
        if not ready_at_str:
            return None

        try:
            ready_at = datetime.fromisoformat(ready_at_str)
        except (ValueError, TypeError):
            return None

        timeout = timedelta(minutes=gate_config.timeout_minutes)
        elapsed = datetime.now() - ready_at

        if elapsed < timeout:
            return None  # No timeout yet

        # Timeout has elapsed - apply policy
        policy = gate_config.timeout_policy.value
        self.console._console.print()
        self.console.warn(
            f"⏱ Gate '{gate_config.name}' has timed out after {elapsed.total_seconds() / 60:.1f} minutes"
        )

        if policy == "reject":
            self.console.error("Timeout policy: [red]REJECT[/red]")
            return False
        elif policy == "cancel":
            self.console.error("Timeout policy: [red]CANCEL SESSION[/red]")
            return False
        elif policy == "auto":
            self.console.warning("Timeout policy: [yellow]AUTO-APPROVE[/yellow]")
            self.console.success("Gate auto-approved due to timeout")
            return True

        return None

    def _show_gate_header(self, gate_config: GateConfig) -> None:
        """Display gate header information.

        Args:
            gate_config: Gate configuration to display
        """
        self.console._console.print()
        self.console.print("[bold yellow]=[/bold yellow]" * 50)
        self.console.print(f"[bold yellow]⚠ Gate: {gate_config.name}[/bold yellow]")
        self.console.print("[bold yellow]=[/bold yellow]" * 50)
        self.console._console.print()

        if gate_config.description:
            self.console.print(f"[dim]{gate_config.description}[/dim]")
            self.console._console.print()

    def _show_required_artifacts(
        self,
        gate_config: GateConfig,
        session_id: str,
    ) -> list[str]:
        """Show required artifacts and check existence.

        Checks in order:
        1. Session artifacts directory
        2. Project root directory (with path validation)

        Args:
            gate_config: Gate configuration
            session_id: Session ID for loading artifacts

        Returns:
            List of missing artifact names
        """
        if not gate_config.required_artifacts:
            return []

        self.console.print("[bold]Required Artifacts:[/bold]")
        missing = []

        for pattern in gate_config.required_artifacts:
            if not validate_artifact_pattern(pattern, self.project_root):
                self.console.error(f"  ✗ {pattern} [dim](invalid pattern)[/dim]")
                missing.append(pattern)
                continue

            found = False

            # Check for wildcards
            if "*" in pattern or "?" in pattern:
                # List all session artifacts and filter
                # Ideally we'd use a store.glob() method if available, but list+filter works for now
                try:
                    # Access underlying DB interface for listing if not exposed on store directly
                    # Or assume store.list_artifacts returns paths/names? No, store.list_artifacts returns paths.
                    # But store is WorkflowSessionStore. list_artifacts(session_id) returns list[Path].
                    # Let's use the DB interface if possible for efficiency, or store.list_artifacts.
                    # store.list_artifacts uses DB list.
                    self.store.list_artifacts(session_id)
                    # The artifact list logic returns resolved paths (e.g. /abs/path/to/art).
                    # We need the logical names relative to artifacts dir.
                    # Let's use db.artifacts.list_page() directly if we can access _get_db().
                    # self.store._get_db().artifacts.list_page(session_id) returns dicts.

                    db = self.store._get_db()
                    rows = db.artifacts.list_page(session_id=session_id, limit=5000)
                    logical_paths = [r.get("path") or r.get("name") for r in rows]

                    matches = fnmatch.filter(logical_paths, pattern)
                    if matches:
                        found = True
                        for match in matches[:3]:
                            self.console.meta(f"  ✓ {match} [dim](session glob)[/dim]")
                            content = self.store.load_artifact(session_id, match)
                            if content:
                                self._show_content_preview(content)
                        if len(matches) > 3:
                            self.console.print(f"    [dim]... and {len(matches) - 3} more[/dim]")
                except Exception:
                    pass
            else:
                # Exact match
                content = self.store.load_artifact(session_id, pattern)
                if content:
                    self.console.meta(f"  ✓ {pattern} [dim](session)[/dim]")
                    self._show_content_preview(content)
                    found = True

            if not found:
                self.console.error(f"  ✗ {pattern} [dim](not found)[/dim]")
                missing.append(pattern)

        self.console._console.print()
        return missing

    def _show_content_preview(self, content: str) -> None:
        """Show preview of content string."""
        lines = content.split("\n")
        preview = "\n".join(lines[:5])
        if len(lines) > 5:
            preview += "\n..."
        self.console.print(f"    [dim]{preview[:200]}...[/dim]")

    def _show_file_preview(self, path: Path) -> None:
        """Show preview of file content."""
        try:
            content = path.read_text()
            self._show_content_preview(content)
        except Exception:
            self.console.print("    [dim](unreadable)[/dim]")

    def _get_user_approval(
        self,
        gate_config: GateConfig,
        session_id: str,
        node_id: str,
    ) -> bool:
        """Get user approval decision.

        Args:
            gate_config: Gate configuration
            session_id: Session ID
            node_id: Gate node ID

        Returns:
            True if approved, False if rejected
        """
        from rich.prompt import Prompt

        self.console.print("[bold]Options:[/bold]")
        self.console.meta("  [green]yes[/green] / [green]y[/green]     - Approve and continue")
        self.console.meta("  [red]no[/red] / [red]n[/red]       - Reject and pause workflow")
        self.console.meta("  [cyan]view[/cyan] / [cyan]v[/cyan]  - View full artifact content")
        if gate_config.timeout_policy.value != "reject":
            self.console.meta("  [cyan]skip[/cyan] / [cyan]s[/cyan]  - Skip this gate")
        self.console._console.print()

        while True:
            try:
                # Don't use Rich's choices parameter - it's too restrictive
                # We handle validation ourselves for better UX
                response = Prompt.ask(
                    "[bold]Approve gate?[/bold]",
                    default="yes",
                    console=self.console._console,
                )

                response = response.strip().strip("'\"").lower()

                if response in ("yes", "y"):
                    self.console.success("Gate approved!")
                    return True
                elif response in ("no", "n"):
                    reason = Prompt.ask(
                        "[dim]Rejection reason (press Enter to skip)[/dim]",
                        default="",
                        console=self.console._console,
                    )
                    self.last_rejection_reason = reason.strip() or None
                    self.console.warn("Gate rejected.")
                    return False
                elif response in ("view", "v"):
                    self._show_full_artifacts(session_id, gate_config.required_artifacts)
                    # Continue prompting after viewing
                    continue
                elif response in ("skip", "s"):
                    # Only allow skip if not in reject mode
                    if gate_config.timeout_policy.value == "reject":
                        self.console.warn("Skip not allowed for this gate (timeout policy: reject)")
                        continue
                    else:
                        self.console.warning("Gate skipped!")
                        return True
                else:
                    self.console.warn(
                        f"Unknown response: '{response}'. Enter 'yes', 'no', 'view', or 'skip'"
                    )

            except (EOFError, KeyboardInterrupt):
                self.console.warn("\nGate cancelled.")
                return False
            except Exception as e:
                self.console.error(f"Error reading input: {e}")
                return False

    def _show_full_artifacts(self, session_id: str, patterns: list[str]) -> None:
        """Show full artifact content.

        Args:
            session_id: Session ID
            patterns: Artifact patterns to show
        """
        for pattern in patterns:
            if not validate_artifact_pattern(pattern, self.project_root):
                self.console.error(f"Artifact '{pattern}' has invalid pattern")
                continue

            found = False

            # Check for wildcards
            if "*" in pattern or "?" in pattern:
                try:
                    db = self.store._get_db()
                    rows = db.artifacts.list_page(session_id=session_id, limit=5000)
                    logical_paths = [r.get("path") or r.get("name") for r in rows]
                    matches = fnmatch.filter(logical_paths, pattern)

                    if matches:
                        found = True
                        for match in matches:
                            content = self.store.load_artifact(session_id, match)
                            if content:
                                self._print_artifact_content(match, content)
                except Exception:
                    pass
            else:
                # Exact match
                content = self.store.load_artifact(session_id, pattern)
                if content:
                    self._print_artifact_content(pattern, content)
                    found = True

            if not found:
                self.console.warn(f"Artifact '{pattern}' not found")

    def _print_artifact_content(self, name: str, content: str) -> None:
        """Print artifact content with header."""
        self.console._console.print()
        self.console.print(f"[bold]{name}:[/bold]")
        self.console._console.print()
        # Truncate if too long
        if len(content) > 2000:
            content = content[:2000] + "\n\n... (truncated)"
        self.console.print(content)

    def _print_file_content(self, name: str, path: Path) -> None:
        """Print file content with header."""
        self.console._console.print()
        self.console.print(f"[bold]{name}:[/bold]")
        self.console._console.print()
        try:
            content = path.read_text()
            # Truncate if too long
            if len(content) > 2000:
                content = content[:2000] + "\n\n... (truncated)"
            self.console.print(content)
        except Exception as e:
            self.console.error(f"Error reading artifact: {e}")

    @staticmethod
    def auto_approve(gate_config: GateConfig) -> bool:
        """Auto-approve a gate (for --yes flag).

        Args:
            gate_config: Gate configuration

        Returns:
            True (always approved)
        """
        console.warning(f"Auto-approving gate: {gate_config.name}")
        return True

__all__ = ["InteractiveGateHandler", "validate_artifact_pattern"]
