"""Rules file loader."""

from __future__ import annotations

from pathlib import Path

from pixl.loaders.types import LoadedRule


class RulesLoader:
    """Loader for rule files."""

    # Common rule file locations
    RULE_LOCATIONS = [
        ".claude/rules",
        ".cursorrules",
        ".github/copilot-instructions.md",
    ]

    def __init__(self, project_path: Path):
        """Initialize loader.

        Args:
            project_path: Project root path
        """
        self.project_path = project_path
        self.rules_dir = project_path / ".claude" / "rules"

    def list_rules(self) -> list[Path]:
        """List all rule files.

        Returns:
            List of paths to rule files
        """
        rules = []

        # Check .claude/rules directory
        if self.rules_dir.exists():
            rules.extend(sorted(self.rules_dir.glob("*.md")))

        # Check .cursorrules file
        cursorrules = self.project_path / ".cursorrules"
        if cursorrules.exists():
            rules.append(cursorrules)

        # Check .github/copilot-instructions.md
        copilot = self.project_path / ".github" / "copilot-instructions.md"
        if copilot.exists():
            rules.append(copilot)

        return rules

    def load_rule(self, path: Path) -> LoadedRule | None:
        """Load a single rule file.

        Args:
            path: Path to rule file

        Returns:
            LoadedRule or None if invalid
        """
        try:
            content = path.read_text()
        except (OSError, UnicodeDecodeError):
            return None

        # Determine name from file
        if path.name == ".cursorrules":
            name = "cursorrules"
        elif path.name == "copilot-instructions.md":
            name = "copilot-instructions"
        else:
            name = path.stem

        return LoadedRule(
            name=name,
            path=str(path),
            content=content,
        )

    def load_all(self) -> list[LoadedRule]:
        """Load all rule files.

        Returns:
            List of loaded rules
        """
        rules = []
        for path in self.list_rules():
            rule = self.load_rule(path)
            if rule:
                rules.append(rule)
        return rules


def load_rules(project_path: Path) -> list[LoadedRule]:
    """Load all rules from project.

    Args:
        project_path: Project root path

    Returns:
        List of loaded rules
    """
    loader = RulesLoader(project_path)
    return loader.load_all()
