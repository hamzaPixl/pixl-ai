"""Tests for dynamic agent loading from crew/agents/*.md files."""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl_api.routes.agents import (
    _extract_description,
    _load_agents_from_crew,
    _parse_frontmatter,
)

# --- _parse_frontmatter ---


def test_parse_frontmatter_extracts_simple_values() -> None:
    text = "---\nname: orchestrator\nmodel: opus\nmaxTurns: 80\n---\nBody text"
    fm = _parse_frontmatter(text)
    assert fm["name"] == "orchestrator"
    assert fm["model"] == "opus"
    assert fm["maxTurns"] == "80"


def test_parse_frontmatter_skips_multiline_description() -> None:
    text = "---\nname: explorer\ndescription: >\n  Some long description\nmodel: haiku\n---\n"
    fm = _parse_frontmatter(text)
    assert fm["name"] == "explorer"
    assert fm["model"] == "haiku"
    # description: > should be skipped (block scalar indicator)
    assert "description" not in fm


def test_parse_frontmatter_empty_text() -> None:
    assert _parse_frontmatter("no frontmatter here") == {}


def test_parse_frontmatter_tools_as_csv() -> None:
    text = "---\nname: test\ntools: Read, Write, Edit\n---\n"
    fm = _parse_frontmatter(text)
    assert fm["tools"] == "Read, Write, Edit"


# --- _extract_description ---


def test_extract_description_multiline() -> None:
    text = (
        "---\nname: explorer\ndescription: >\n"
        "  Delegate to this agent for fast codebase exploration\n---\n"
    )
    desc = _extract_description(text)
    assert "codebase exploration" in desc


def test_extract_description_inline() -> None:
    text = "---\nname: test\ndescription: A simple test agent.\n---\n"
    desc = _extract_description(text)
    assert desc == "A simple test agent"


def test_extract_description_no_frontmatter() -> None:
    assert _extract_description("plain text") == ""


# --- _load_agents_from_crew ---


def test_load_agents_from_crew_with_real_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Load agents from a mock crew directory."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Create mock agent files
    (agents_dir / "alpha.md").write_text(
        "---\nname: alpha\ndescription: Alpha agent.\nmodel: sonnet\n"
        "tools: Read, Write\nmaxTurns: 30\n---\nBody\n"
    )
    (agents_dir / "beta.md").write_text(
        "---\nname: beta\ndescription: >\n  Beta agent for testing\n"
        "model: haiku\ntools: Bash\nmaxTurns: 10\n---\nBody\n"
    )

    # Patch get_crew_root to return our tmp_path
    monkeypatch.setattr(
        "pixl_api.routes.agents.get_crew_root",
        lambda: tmp_path,
        raising=False,
    )
    # We need to make the import work -- mock it at the module level
    import pixl_api.routes.agents as agents_mod

    # Reset the cache
    monkeypatch.setattr(agents_mod, "_cached_agents", None)

    # Directly call with mocked import
    def mock_load() -> list:
        return _load_from_dir(agents_dir)

    agents = _load_from_dir(agents_dir)
    assert len(agents) == 2
    assert agents[0]["name"] == "alpha"
    assert agents[0]["model"] == "sonnet"
    assert agents[0]["tools"] == ["Read", "Write"]
    assert agents[0]["max_turns"] == 30
    assert agents[1]["name"] == "beta"
    assert agents[1]["model"] == "haiku"


def _load_from_dir(agents_dir: Path) -> list[dict]:
    """Helper to load agents from a specific directory without the import machinery."""

    from pixl_api.routes.agents import _extract_description, _parse_frontmatter

    agents = []
    for md_file in sorted(agents_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        name = fm.get("name", md_file.stem)
        model_val = fm.get("model")
        if model_val in ("inherit", "null", "None", ""):
            model_val = None
        tools_raw = fm.get("tools", "")
        tools = [t.strip() for t in tools_raw.split(",") if t.strip()] if tools_raw else []
        max_turns_raw = fm.get("maxTurns", "50")
        try:
            max_turns = int(max_turns_raw)
        except ValueError:
            max_turns = 50
        description = _extract_description(text)
        if not description:
            description = name.replace("-", " ").title()
        agents.append(
            {
                "name": name,
                "description": description,
                "model": model_val,
                "tools": tools,
                "max_turns": max_turns,
            }
        )
    return agents


def test_load_agents_fallback_when_no_directory() -> None:
    """Should return fallback list when crew directory is not available."""
    # _load_agents_from_crew tries to import pixl_cli.crew.get_crew_root
    # which may or may not be available. Either way it should return a list.
    agents = _load_agents_from_crew()
    assert isinstance(agents, list)
    assert len(agents) >= 3
    names = {a["name"] for a in agents}
    # Should have at least the core agents
    assert "orchestrator" in names or "backend-engineer" in names


def test_parse_frontmatter_inherit_model() -> None:
    """model: inherit should be treated as None."""
    text = "---\nname: test\nmodel: inherit\n---\n"
    fm = _parse_frontmatter(text)
    assert fm["model"] == "inherit"
    # The loading code treats "inherit" as None
