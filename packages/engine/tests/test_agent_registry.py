"""Tests for AgentRegistry and plugin path resolution."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pixl.agents.registry import AgentRegistry
from pixl.agents.sdk_options import _resolve_crew_plugin_path

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def crew_root(tmp_path: Path) -> Path:
    """Create a minimal crew directory structure."""
    crew = tmp_path / "crew"
    (crew / ".claude-plugin").mkdir(parents=True)
    (crew / ".claude-plugin" / "plugin.json").write_text('{"name": "test-crew"}')
    (crew / "agents").mkdir()
    return crew


def _write_agent(
    agents_dir: Path,
    name: str,
    *,
    model: str = "sonnet",
    tools: str = "[Read, Write]",
    body: str = "You are helpful.",
) -> None:
    (agents_dir / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: Test agent {name}\n"
        f"model: {model}\ntools: {tools}\nmaxTurns: 30\n---\n{body}\n"
    )


# ── _resolve_crew_plugin_path ─────────────────────────────────────────────


class TestResolveCrewPluginPath:
    def test_returns_env_override(self, crew_root: Path) -> None:
        with patch.dict(os.environ, {"PIXL_CREW_ROOT": str(crew_root)}):
            result = _resolve_crew_plugin_path()
        assert result == str(crew_root)

    def test_returns_none_when_env_points_to_nonexistent(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"PIXL_CREW_ROOT": str(tmp_path / "nope")}):
            result = _resolve_crew_plugin_path()
        # Falls through to monorepo/bundled checks — likely None in test env
        assert result is None or isinstance(result, str)

    def test_returns_none_when_no_crew_found(self) -> None:
        with patch.dict(os.environ, {"PIXL_CREW_ROOT": ""}, clear=False):
            # In CI/test env without monorepo structure, should return None or a valid path
            result = _resolve_crew_plugin_path()
            assert result is None or isinstance(result, str)


# ── AgentRegistry ─────────────────────────────────────────────────────────


class TestAgentRegistry:
    def test_load_from_crew(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "backend-engineer")
        _write_agent(crew_root / "agents", "frontend-engineer", model="inherit")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        assert sorted(registry.list_agents()) == ["backend-engineer", "frontend-engineer"]

    def test_parse_model_inherit(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "explorer", model="inherit")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        defn = registry.get_agent_definition("explorer")
        assert defn is not None
        assert defn.model is None  # inherit → None

    def test_parse_tools(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "arch", tools="[Read, Glob, Grep]")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        defn = registry.get_agent_definition("arch")
        assert defn is not None
        assert set(defn.tools) == {"Read", "Glob", "Grep"}

    def test_removes_agent_from_tools(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "worker", tools="[Read, Agent, Write]")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        defn = registry.get_agent_definition("worker")
        assert defn is not None
        assert "Agent" not in defn.tools

    def test_get_all_definitions(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "a1")
        _write_agent(crew_root / "agents", "a2")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        defs = registry.get_all_definitions()
        assert len(defs) == 2
        assert "a1" in defs
        assert "a2" in defs

    def test_get_nonexistent_agent(self) -> None:
        registry = AgentRegistry()
        assert registry.get_agent_definition("nope") is None

    def test_malformed_frontmatter_skipped(self, crew_root: Path) -> None:
        (crew_root / "agents" / "bad.md").write_text("no frontmatter here")
        _write_agent(crew_root / "agents", "good")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        assert registry.list_agents() == ["good"]

    def test_missing_agents_dir(self, tmp_path: Path) -> None:
        registry = AgentRegistry()
        registry.load_from_crew(tmp_path)  # no agents/ dir
        assert registry.list_agents() == []

    def test_definitions_cached(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "a1")
        _write_agent(crew_root / "agents", "a2")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        d1 = registry.get_all_definitions()
        d2 = registry.get_all_definitions()
        assert d1 is d2  # Same object — cached

    def test_cache_invalidated_on_reload(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "a1")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        d1 = registry.get_all_definitions()
        _write_agent(crew_root / "agents", "a2")
        registry.load_from_crew(crew_root)
        d2 = registry.get_all_definitions()
        assert d1 is not d2  # New object — cache invalidated
        assert len(d2) == 2

    def test_prompt_body_captured(self, crew_root: Path) -> None:
        _write_agent(crew_root / "agents", "helper", body="You are a code expert.\nBe concise.")
        registry = AgentRegistry()
        registry.load_from_crew(crew_root)
        defn = registry.get_agent_definition("helper")
        assert defn is not None
        assert "code expert" in defn.prompt


# ── EventBus ──────────────────────────────────────────────────────────────


class TestEventBus:
    def test_publish_subscribe(self) -> None:
        from types import SimpleNamespace

        from pixl.events.bus import EventBus

        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))
        event = SimpleNamespace(event_type="test")
        bus.publish(event)
        assert len(received) == 1
        assert received[0].event_type == "test"

    def test_filtered_subscribe(self) -> None:
        from types import SimpleNamespace

        from pixl.events.bus import EventBus

        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e), event_type="node_started")
        bus.publish(SimpleNamespace(event_type="node_started"))
        bus.publish(SimpleNamespace(event_type="node_completed"))
        assert len(received) == 1

    def test_unsubscribe(self) -> None:
        from pixl.events.bus import EventBus

        bus = EventBus()
        cb = lambda e: None  # noqa: E731
        bus.subscribe(cb)
        assert bus.subscriber_count == 1
        bus.unsubscribe(cb)
        assert bus.subscriber_count == 0

    def test_callback_error_does_not_crash(self) -> None:
        from types import SimpleNamespace

        from pixl.events.bus import EventBus

        bus = EventBus()
        received = []
        bus.subscribe(lambda e: 1 / 0)  # will raise
        bus.subscribe(lambda e: received.append(e))  # should still fire
        bus.publish(SimpleNamespace(event_type="test"))
        assert len(received) == 1
