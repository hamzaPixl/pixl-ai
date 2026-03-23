"""YAML frontmatter parser for markdown files."""

from __future__ import annotations

import re
from typing import Any


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown.

    Args:
        content: Markdown content with optional frontmatter

    Returns:
        Tuple of (frontmatter_dict, body)
    """
    if not content.startswith("---"):
        return {}, content

    end_match = re.search(r"^---\s*$", content[3:], re.MULTILINE)
    if not end_match:
        return {}, content

    frontmatter_text = content[3 : 3 + end_match.start()]
    body = content[3 + end_match.end() :].strip()

    # Simple YAML parsing (no external deps)
    frontmatter: dict[str, Any] = {}
    for line in frontmatter_text.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key == "skills" and value:
                frontmatter[key] = [s.strip() for s in value.split(",")]
            elif (
                value.startswith('"')
                and value.endswith('"')
                or value.startswith("'")
                and value.endswith("'")
            ):
                frontmatter[key] = value[1:-1]
            else:
                frontmatter[key] = value

    return frontmatter, body
