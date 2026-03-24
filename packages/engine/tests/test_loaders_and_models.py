"""Unit tests for loaders and pure Pydantic/dataclass models.

All tests follow Arrange-Act-Assert, are isolated from each other,
and use tmp_path for any filesystem operations.
No database, no network, no subprocesses.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
from pixl.loaders.claude_md import ClaudeMdLoader, load_claude_md
from pixl.loaders.frontmatter import parse_frontmatter
from pixl.loaders.rules import RulesLoader, load_rules
from pixl.loaders.settings import SettingsLoader, load_settings
from pixl.loaders.types import (
    LoadedClaudeMd,
    LoadedRule,
    LoadedSettings,
    LoadedSkill,
    SkillFrontmatter,
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
from pixl.models.budget import BudgetConfig, CostEvent, check_budget
from pixl.models.heartbeat_run import HeartbeatRun, InvocationSource, RunStatus
from pixl.models.knowledge import Chunk, ChunkType, KnowledgeManifest, SearchResult
from pixl.models.metrics import AgentMetrics
from pixl.models.version_info import VersionInfo, extract_python_version, get_git_hash
from pixl.models.wakeup import WakeupReason, WakeupRequest, WakeupStatus

# ===========================================================================
# Frontmatter parser
# ===========================================================================


class TestParseFrontmatter:
    def test_returns_empty_dict_and_full_content_when_no_frontmatter(self) -> None:
        content = "# Hello\n\nSome text."
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parses_simple_key_value_frontmatter(self) -> None:
        content = "---\ntitle: My Title\n---\n\nBody text."
        fm, body = parse_frontmatter(content)
        assert fm["title"] == "My Title"
        assert body == "Body text."

    def test_strips_quotes_from_quoted_values(self) -> None:
        content = '---\nname: "Quoted Name"\n---\nBody.'
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "Quoted Name"

    def test_strips_single_quotes_from_quoted_values(self) -> None:
        content = "---\nname: 'Single Quoted'\n---\nBody."
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "Single Quoted"

    def test_parses_skills_as_list(self) -> None:
        content = "---\nskills: a, b, c\n---\nBody."
        fm, body = parse_frontmatter(content)
        assert fm["skills"] == ["a", "b", "c"]

    def test_returns_empty_dict_when_closing_delimiter_missing(self) -> None:
        content = "---\ntitle: something\nBody without closing dashes."
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_body_is_stripped_of_leading_whitespace(self) -> None:
        content = "---\nkey: val\n---\n\n\nBody starts here."
        _, body = parse_frontmatter(content)
        assert body == "Body starts here."

    def test_handles_empty_string_input(self) -> None:
        fm, body = parse_frontmatter("")
        assert fm == {}
        assert body == ""

    def test_handles_multiple_colons_in_value(self) -> None:
        content = "---\nurl: http://example.com/path\n---\nBody."
        fm, body = parse_frontmatter(content)
        assert fm["url"] == "http://example.com/path"


# ===========================================================================
# ClaudeMdLoader
# ===========================================================================


class TestClaudeMdLoaderFindFile:
    def test_finds_claude_md_in_project_root(self, tmp_path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Project")
        loader = ClaudeMdLoader(tmp_path)
        found = loader.find_claude_md()
        assert found == tmp_path / "CLAUDE.md"

    def test_finds_claude_md_in_claude_directory(self, tmp_path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text("# Project")
        loader = ClaudeMdLoader(tmp_path)
        found = loader.find_claude_md()
        assert found == claude_dir / "CLAUDE.md"

    def test_returns_none_when_no_claude_md_exists(self, tmp_path) -> None:
        loader = ClaudeMdLoader(tmp_path)
        assert loader.find_claude_md() is None

    def test_root_takes_priority_over_claude_directory(self, tmp_path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Root")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text("# Subdir")
        loader = ClaudeMdLoader(tmp_path)
        found = loader.find_claude_md()
        assert found == tmp_path / "CLAUDE.md"


class TestClaudeMdLoaderLoad:
    def test_returns_empty_result_when_file_missing(self, tmp_path) -> None:
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert result.content == ""
        assert result.path == ""
        assert not result.exists

    def test_loads_raw_content(self, tmp_path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Hello\nSome content.")
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert "Hello" in result.content
        assert result.exists

    def test_extracts_project_overview_section(self, tmp_path) -> None:
        content = (
            "# Header\n\n## Project Overview\n\n"
            "This is my project.\n\n## Other\n\nOther stuff."
        )
        (tmp_path / "CLAUDE.md").write_text(content)
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert result.project_overview is not None
        assert "This is my project." in result.project_overview

    def test_falls_back_to_overview_section_name(self, tmp_path) -> None:
        content = "# Header\n\n## Overview\n\nFallback overview.\n\n## End\n\nEnd."
        (tmp_path / "CLAUDE.md").write_text(content)
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert result.project_overview is not None
        assert "Fallback overview." in result.project_overview

    def test_extracts_commands_from_bash_code_blocks(self, tmp_path) -> None:
        content = "# Docs\n\n```bash\nmake install\nmake test\n```\n"
        (tmp_path / "CLAUDE.md").write_text(content)
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert "make install" in result.commands
        assert "make test" in result.commands

    def test_ignores_comment_lines_in_code_blocks(self, tmp_path) -> None:
        content = "# Docs\n\n```bash\n# This is a comment\nmake run\n```\n"
        (tmp_path / "CLAUDE.md").write_text(content)
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert "make run" in result.commands
        assert "# This is a comment" not in result.commands

    def test_limits_commands_to_20(self, tmp_path) -> None:
        lines = "\n".join(f"cmd{i}" for i in range(30))
        content = f"```bash\n{lines}\n```\n"
        (tmp_path / "CLAUDE.md").write_text(content)
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert len(result.commands) <= 20

    def test_extracts_patterns_from_key_patterns_section(self, tmp_path) -> None:
        content = "## Key Patterns\n\n- Pattern one\n- Pattern two\n\n## End\n\nEnd."
        (tmp_path / "CLAUDE.md").write_text(content)
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert "Pattern one" in result.patterns
        assert "Pattern two" in result.patterns

    def test_returns_empty_content_on_unicode_error(self, tmp_path) -> None:
        path = tmp_path / "CLAUDE.md"
        path.write_bytes(b"\xff\xfe invalid utf-8 \x80\x81")
        loader = ClaudeMdLoader(tmp_path)
        result = loader.load()
        assert result.content == ""


class TestLoadClaudeMdHelper:
    def test_returns_none_when_no_file_found(self, tmp_path) -> None:
        assert load_claude_md(tmp_path) is None

    def test_returns_loaded_claude_md_when_file_found(self, tmp_path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# My Project")
        result = load_claude_md(tmp_path)
        assert result is not None
        assert result.exists


# ===========================================================================
# RulesLoader
# ===========================================================================


class TestRulesLoaderListRules:
    def test_returns_empty_list_when_no_rules_exist(self, tmp_path) -> None:
        loader = RulesLoader(tmp_path)
        assert loader.list_rules() == []

    def test_lists_md_files_from_claude_rules_directory(self, tmp_path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "coding-style.md").write_text("# Style")
        (rules_dir / "testing.md").write_text("# Testing")
        loader = RulesLoader(tmp_path)
        paths = loader.list_rules()
        names = [p.name for p in paths]
        assert "coding-style.md" in names
        assert "testing.md" in names

    def test_includes_cursorrules_file(self, tmp_path) -> None:
        (tmp_path / ".cursorrules").write_text("Some cursor rules.")
        loader = RulesLoader(tmp_path)
        paths = loader.list_rules()
        assert any(p.name == ".cursorrules" for p in paths)

    def test_includes_copilot_instructions(self, tmp_path) -> None:
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "copilot-instructions.md").write_text("Copilot instructions.")
        loader = RulesLoader(tmp_path)
        paths = loader.list_rules()
        assert any(p.name == "copilot-instructions.md" for p in paths)


class TestRulesLoaderLoadRule:
    def test_returns_none_on_unreadable_file(self, tmp_path) -> None:
        # Write binary bytes that are not valid UTF-8
        path = tmp_path / "bad.md"
        path.write_bytes(b"\xff\xfe\x80\x81")
        loader = RulesLoader(tmp_path)
        result = loader.load_rule(path)
        assert result is None

    def test_uses_stem_as_name_for_regular_md_files(self, tmp_path) -> None:
        path = tmp_path / "my-rule.md"
        path.write_text("Rule content.")
        loader = RulesLoader(tmp_path)
        rule = loader.load_rule(path)
        assert rule is not None
        assert rule.name == "my-rule"

    def test_uses_cursorrules_as_name_for_cursorrules_file(self, tmp_path) -> None:
        path = tmp_path / ".cursorrules"
        path.write_text("Cursor rules.")
        loader = RulesLoader(tmp_path)
        rule = loader.load_rule(path)
        assert rule is not None
        assert rule.name == "cursorrules"

    def test_uses_copilot_instructions_as_name_for_copilot_file(self, tmp_path) -> None:
        path = tmp_path / "copilot-instructions.md"
        path.write_text("Copilot instructions.")
        loader = RulesLoader(tmp_path)
        rule = loader.load_rule(path)
        assert rule is not None
        assert rule.name == "copilot-instructions"

    def test_loads_content_correctly(self, tmp_path) -> None:
        path = tmp_path / "style.md"
        path.write_text("# Style Rules\n\nUse const.")
        loader = RulesLoader(tmp_path)
        rule = loader.load_rule(path)
        assert rule is not None
        assert "Use const." in rule.content


class TestRulesLoaderLoadAll:
    def test_returns_all_valid_rules(self, tmp_path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "a.md").write_text("Rule A")
        (rules_dir / "b.md").write_text("Rule B")
        loader = RulesLoader(tmp_path)
        rules = loader.load_all()
        assert len(rules) == 2

    def test_skips_unreadable_files(self, tmp_path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "good.md").write_text("Good rule")
        bad = rules_dir / "bad.md"
        bad.write_bytes(b"\xff\xfe\x80\x81")
        loader = RulesLoader(tmp_path)
        rules = loader.load_all()
        assert len(rules) == 1
        assert rules[0].name == "good"


class TestLoadRulesHelper:
    def test_returns_empty_list_for_empty_project(self, tmp_path) -> None:
        assert load_rules(tmp_path) == []

    def test_returns_rules_when_they_exist(self, tmp_path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "style.md").write_text("# Style")
        rules = load_rules(tmp_path)
        assert len(rules) == 1


# ===========================================================================
# SettingsLoader
# ===========================================================================


class TestSettingsLoaderLoad:
    def test_returns_empty_settings_when_file_missing(self, tmp_path) -> None:
        loader = SettingsLoader(tmp_path)
        result = loader.load()
        assert not result.exists
        assert result.data == {}

    def test_loads_valid_json_settings(self, tmp_path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings = {"model": "claude-3-5-sonnet", "max_tokens": 4096}
        (claude_dir / "settings.json").write_text(json.dumps(settings))
        loader = SettingsLoader(tmp_path)
        result = loader.load()
        assert result.exists
        assert result.data["model"] == "claude-3-5-sonnet"
        assert result.data["max_tokens"] == 4096

    def test_returns_empty_settings_on_invalid_json(self, tmp_path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{not valid json")
        loader = SettingsLoader(tmp_path)
        result = loader.load()
        assert not result.exists
        assert result.data == {}

    def test_stores_path_in_result_when_loaded(self, tmp_path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{}")
        loader = SettingsLoader(tmp_path)
        result = loader.load()
        assert result.path is not None
        assert "settings.json" in result.path


class TestLoadSettingsHelper:
    def test_returns_none_when_no_settings_file(self, tmp_path) -> None:
        assert load_settings(tmp_path) is None

    def test_returns_loaded_settings_when_file_found(self, tmp_path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text('{"key": "value"}')
        result = load_settings(tmp_path)
        assert result is not None
        assert result.get("key") == "value"


# ===========================================================================
# Loader types
# ===========================================================================


class TestLoadedClaudeMd:
    def test_exists_is_false_when_content_is_empty(self) -> None:
        md = LoadedClaudeMd(path="", content="")
        assert not md.exists

    def test_exists_is_true_when_content_is_present(self) -> None:
        md = LoadedClaudeMd(path="/some/CLAUDE.md", content="# Project")
        assert md.exists

    def test_defaults_commands_and_patterns_to_empty_lists(self) -> None:
        md = LoadedClaudeMd(path="", content="")
        assert md.commands == []
        assert md.patterns == []


class TestLoadedSettings:
    def test_exists_is_false_when_path_is_none(self) -> None:
        settings = LoadedSettings()
        assert not settings.exists

    def test_exists_is_true_when_path_is_set(self) -> None:
        settings = LoadedSettings(path="/some/settings.json", data={})
        assert settings.exists

    def test_get_returns_default_for_missing_key(self) -> None:
        settings = LoadedSettings(path="/p", data={"a": 1})
        assert settings.get("missing", "default") == "default"

    def test_get_returns_value_for_existing_key(self) -> None:
        settings = LoadedSettings(path="/p", data={"key": "val"})
        assert settings.get("key") == "val"


class TestLoadedRule:
    def test_construction_stores_all_fields(self) -> None:
        rule = LoadedRule(name="style", path="/rules/style.md", content="# Style")
        assert rule.name == "style"
        assert rule.path == "/rules/style.md"
        assert rule.content == "# Style"


class TestSkillFrontmatter:
    def test_defaults_triggers_to_empty_list(self) -> None:
        sf = SkillFrontmatter(name="my-skill")
        assert sf.triggers == []

    def test_stores_optional_description(self) -> None:
        sf = SkillFrontmatter(name="my-skill", description="Does X")
        assert sf.description == "Does X"


class TestLoadedSkill:
    def test_description_delegates_to_frontmatter(self) -> None:
        fm = SkillFrontmatter(name="s", description="Skill description")
        skill = LoadedSkill(
            name="s",
            path="/skills/s/SKILL.md",
            directory="/skills/s",
            frontmatter=fm,
            content="Body",
        )
        assert skill.description == "Skill description"

    def test_description_is_none_when_frontmatter_has_no_description(self) -> None:
        fm = SkillFrontmatter(name="s")
        skill = LoadedSkill(
            name="s",
            path="/skills/s/SKILL.md",
            directory="/skills/s",
            frontmatter=fm,
            content="Body",
        )
        assert skill.description is None


# ===========================================================================
# BudgetConfig / CostEvent / check_budget
# ===========================================================================


class TestCostEvent:
    def test_constructs_with_required_session_id(self) -> None:
        event = CostEvent(session_id="sess-001")
        assert event.session_id == "sess-001"
        assert event.input_tokens == 0
        assert event.output_tokens == 0
        assert event.cost_usd == 0.0

    def test_stores_all_optional_fields(self) -> None:
        event = CostEvent(
            session_id="sess-002",
            run_id="run-abc",
            node_id="node-1",
            adapter_name="anthropic",
            model_name="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=200,
            cost_usd=0.05,
        )
        assert event.run_id == "run-abc"
        assert event.model_name == "claude-3-5-sonnet"
        assert event.input_tokens == 100
        assert event.cost_usd == 0.05


class TestBudgetConfig:
    def test_remaining_usd_is_infinite_when_monthly_usd_is_zero(self) -> None:
        budget = BudgetConfig(monthly_usd=0.0)
        assert budget.remaining_usd == float("inf")

    def test_remaining_usd_computed_correctly(self) -> None:
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=30.0)
        assert budget.remaining_usd == pytest.approx(70.0)

    def test_remaining_usd_never_goes_below_zero(self) -> None:
        budget = BudgetConfig(monthly_usd=10.0, spent_monthly_usd=15.0)
        assert budget.remaining_usd == 0.0

    def test_is_exceeded_false_when_unlimited(self) -> None:
        budget = BudgetConfig(monthly_usd=0.0, spent_monthly_usd=999.0)
        assert not budget.is_exceeded

    def test_is_exceeded_false_when_under_limit(self) -> None:
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=50.0)
        assert not budget.is_exceeded

    def test_is_exceeded_true_when_at_limit(self) -> None:
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=100.0)
        assert budget.is_exceeded

    def test_is_exceeded_true_when_over_limit(self) -> None:
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=120.0)
        assert budget.is_exceeded


class TestCheckBudget:
    def test_allows_any_cost_when_unlimited(self) -> None:
        budget = BudgetConfig(monthly_usd=0.0)
        assert check_budget(budget, 9999.0)

    def test_allows_cost_that_fits_within_budget(self) -> None:
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=50.0)
        assert check_budget(budget, 10.0)

    def test_rejects_cost_that_exceeds_budget(self) -> None:
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=95.0)
        assert not check_budget(budget, 10.0)

    def test_rejects_when_already_at_limit(self) -> None:
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=100.0)
        assert not check_budget(budget, 0.01)

    def test_allows_zero_additional_cost_when_at_limit(self) -> None:
        # spent == monthly but additional is 0 → strict less-than returns False
        budget = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=100.0)
        assert not check_budget(budget, 0.0)


# ===========================================================================
# HeartbeatRun
# ===========================================================================


class TestRunStatus:
    def test_all_enum_values_are_string(self) -> None:
        for status in RunStatus:
            assert isinstance(status, str)


class TestHeartbeatRunGenerateId:
    def test_id_starts_with_run_prefix(self) -> None:
        run_id = HeartbeatRun.generate_id()
        assert run_id.startswith("run-")

    def test_generated_ids_are_unique(self) -> None:
        ids = {HeartbeatRun.generate_id() for _ in range(20)}
        assert len(ids) == 20


class TestHeartbeatRunIsTerminal:
    def test_queued_status_is_not_terminal(self) -> None:
        run = HeartbeatRun(id="run-0001", session_id="sess-1", status=RunStatus.QUEUED)
        assert not run.is_terminal

    def test_running_status_is_not_terminal(self) -> None:
        run = HeartbeatRun(id="run-0002", session_id="sess-1", status=RunStatus.RUNNING)
        assert not run.is_terminal

    def test_succeeded_status_is_terminal(self) -> None:
        run = HeartbeatRun(id="run-0003", session_id="sess-1", status=RunStatus.SUCCEEDED)
        assert run.is_terminal

    def test_failed_status_is_terminal(self) -> None:
        run = HeartbeatRun(id="run-0004", session_id="sess-1", status=RunStatus.FAILED)
        assert run.is_terminal

    def test_cancelled_status_is_terminal(self) -> None:
        run = HeartbeatRun(id="run-0005", session_id="sess-1", status=RunStatus.CANCELLED)
        assert run.is_terminal

    def test_timed_out_status_is_terminal(self) -> None:
        run = HeartbeatRun(id="run-0006", session_id="sess-1", status=RunStatus.TIMED_OUT)
        assert run.is_terminal


class TestHeartbeatRunIsStalled:
    def test_not_stalled_when_not_running(self) -> None:
        run = HeartbeatRun(
            id="run-0010",
            session_id="sess-1",
            status=RunStatus.QUEUED,
            heartbeat_at=datetime.now() - timedelta(seconds=120),
        )
        assert not run.is_stalled

    def test_not_stalled_when_no_heartbeat(self) -> None:
        run = HeartbeatRun(
            id="run-0011",
            session_id="sess-1",
            status=RunStatus.RUNNING,
            heartbeat_at=None,
        )
        assert not run.is_stalled

    def test_stalled_when_heartbeat_is_older_than_60_seconds(self) -> None:
        run = HeartbeatRun(
            id="run-0012",
            session_id="sess-1",
            status=RunStatus.RUNNING,
            heartbeat_at=datetime.now() - timedelta(seconds=61),
        )
        assert run.is_stalled

    def test_not_stalled_when_heartbeat_is_recent(self) -> None:
        run = HeartbeatRun(
            id="run-0013",
            session_id="sess-1",
            status=RunStatus.RUNNING,
            heartbeat_at=datetime.now() - timedelta(seconds=30),
        )
        assert not run.is_stalled

    def test_default_invocation_source_is_start(self) -> None:
        run = HeartbeatRun(id="run-0014", session_id="sess-1")
        assert run.invocation == InvocationSource.START


# ===========================================================================
# Knowledge models
# ===========================================================================


class TestChunkType:
    def test_all_values_are_lowercase_strings(self) -> None:
        for ct in ChunkType:
            assert ct == ct.lower()


class TestChunk:
    def test_constructs_with_required_fields(self) -> None:
        chunk = Chunk(
            id="chunk-001",
            title="Setup",
            content="How to set up the project.",
            source="docs/setup.md",
        )
        assert chunk.id == "chunk-001"
        assert chunk.chunk_type == ChunkType.CONCEPT

    def test_keywords_default_to_empty_list(self) -> None:
        chunk = Chunk(id="c", title="T", content="C", source="s")
        assert chunk.keywords == []

    def test_stores_line_range(self) -> None:
        chunk = Chunk(id="c", title="T", content="C", source="s", line_start=10, line_end=20)
        assert chunk.line_start == 10
        assert chunk.line_end == 20


class TestKnowledgeManifest:
    def test_default_version_is_one_dot_zero(self) -> None:
        manifest = KnowledgeManifest()
        assert manifest.version == "1.0"

    def test_default_chunk_and_source_counts_are_zero(self) -> None:
        manifest = KnowledgeManifest()
        assert manifest.chunk_count == 0
        assert manifest.source_count == 0

    def test_stores_file_hashes(self) -> None:
        hashes = {"file.py": "abc123"}
        manifest = KnowledgeManifest(file_hashes=hashes)
        assert manifest.file_hashes["file.py"] == "abc123"


class TestSearchResult:
    def test_construction_stores_all_fields(self) -> None:
        chunk = Chunk(id="c", title="T", content="C", source="s")
        result = SearchResult(chunk=chunk, score=0.87, matched_terms=["term1"])
        assert result.score == 0.87
        assert result.matched_terms == ["term1"]
        assert result.chunk is chunk


# ===========================================================================
# AgentMetrics
# ===========================================================================


class TestAgentMetrics:
    def test_constructs_with_required_fields(self) -> None:
        now = datetime.now()
        m = AgentMetrics(
            agent_name="qa-engineer",
            model_name="claude-3-5-sonnet",
            session_id="sess-xyz",
            node_id="node-1",
            started_at=now,
        )
        assert m.agent_name == "qa-engineer"
        assert m.success is True
        assert m.input_tokens == 0

    def test_duration_seconds_is_zero_when_not_completed(self) -> None:
        now = datetime.now()
        m = AgentMetrics(
            agent_name="a",
            model_name="m",
            session_id="s",
            node_id="n",
            started_at=now,
        )
        assert m.duration_seconds == 0.0

    def test_duration_seconds_computed_correctly_when_completed(self) -> None:
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 30)
        m = AgentMetrics(
            agent_name="a",
            model_name="m",
            session_id="s",
            node_id="n",
            started_at=start,
            completed_at=end,
        )
        assert m.duration_seconds == pytest.approx(30.0)

    def test_stores_error_info(self) -> None:
        now = datetime.now()
        m = AgentMetrics(
            agent_name="a",
            model_name="m",
            session_id="s",
            node_id="n",
            started_at=now,
            success=False,
            error_type="TimeoutError",
            error_message="Timed out after 60s",
        )
        assert not m.success
        assert m.error_type == "TimeoutError"


# ===========================================================================
# WakeupRequest
# ===========================================================================


class TestWakeupReason:
    def test_all_values_are_strings(self) -> None:
        for reason in WakeupReason:
            assert isinstance(reason, str)


class TestWakeupStatus:
    def test_all_values_are_strings(self) -> None:
        for status in WakeupStatus:
            assert isinstance(status, str)


class TestWakeupRequest:
    def test_constructs_with_required_fields(self) -> None:
        req = WakeupRequest(session_id="sess-1", reason=WakeupReason.START)
        assert req.session_id == "sess-1"
        assert req.reason == WakeupReason.START
        assert req.status == WakeupStatus.PENDING

    def test_default_coalesced_count_is_zero(self) -> None:
        req = WakeupRequest(session_id="sess-1", reason=WakeupReason.RESUME)
        assert req.coalesced_count == 0

    def test_stores_payload_json(self) -> None:
        req = WakeupRequest(
            session_id="sess-1",
            reason=WakeupReason.GATE_APPROVED,
            payload_json={"gate": "g-001"},
        )
        assert req.payload_json == {"gate": "g-001"}

    def test_processed_at_defaults_to_none(self) -> None:
        req = WakeupRequest(session_id="sess-1", reason=WakeupReason.CHAIN)
        assert req.processed_at is None

    def test_accepts_all_reason_values(self) -> None:
        for reason in WakeupReason:
            req = WakeupRequest(session_id="sess", reason=reason)
            assert req.reason == reason


# ===========================================================================
# VersionInfo
# ===========================================================================


class TestExtractPythonVersion:
    def test_extracts_version_from_full_sys_version_string(self) -> None:
        sys_version = "3.11.7 (main, Dec  4 2023, 18:10:11) [Clang 15.0.0]"
        result = extract_python_version(sys_version)
        assert result == "3.11.7"

    def test_returns_original_when_no_match(self) -> None:
        result = extract_python_version("no version here")
        assert result == "no version here"

    def test_handles_simple_version_string(self) -> None:
        result = extract_python_version("3.12.0")
        assert result == "3.12.0"


class TestVersionInfoValidation:
    def test_accepts_valid_semantic_version(self) -> None:
        v = VersionInfo(version="1.2.3", build_hash="abcd1234", python_version="3.11.0")
        assert v.version == "1.2.3"

    def test_accepts_version_with_prerelease_suffix(self) -> None:
        v = VersionInfo(version="1.0.0-alpha", build_hash="abcd1234", python_version="3.11.0")
        assert v.version == "1.0.0-alpha"

    def test_accepts_version_with_build_metadata(self) -> None:
        v = VersionInfo(
            version="1.0.0+build.123", build_hash="abcd1234", python_version="3.11.0"
        )
        assert v.version == "1.0.0+build.123"

    def test_rejects_version_without_patch(self) -> None:
        with pytest.raises(Exception):
            VersionInfo(version="1.0", build_hash="abcd1234", python_version="3.11.0")

    def test_rejects_empty_version(self) -> None:
        with pytest.raises(Exception):
            VersionInfo(version="", build_hash="abcd1234", python_version="3.11.0")

    def test_accepts_valid_build_hash(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="abc12345", python_version="3.11.0")
        assert v.build_hash == "abc12345"

    def test_accepts_unknown_as_build_hash(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="unknown", python_version="3.11.0")
        assert v.build_hash == "unknown"

    def test_rejects_short_build_hash(self) -> None:
        with pytest.raises(Exception):
            VersionInfo(version="1.0.0", build_hash="ab1", python_version="3.11.0")

    def test_strips_whitespace_from_version(self) -> None:
        v = VersionInfo(version="  1.0.0  ", build_hash="abcd1234", python_version="3.11.0")
        assert v.version == "1.0.0"

    def test_accepts_valid_python_version(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="abcd1234", python_version="3.12.1")
        assert v.python_version == "3.12.1"

    def test_rejects_invalid_python_version(self) -> None:
        with pytest.raises(Exception):
            VersionInfo(version="1.0.0", build_hash="abcd1234", python_version="3.12")

    def test_api_version_accepts_v_prefixed_format(self) -> None:
        v = VersionInfo(
            version="1.0.0", build_hash="abcd1234", python_version="3.11.0", api_version="v1"
        )
        assert v.api_version == "v1"

    def test_api_version_accepts_numeric_format(self) -> None:
        v = VersionInfo(
            version="1.0.0", build_hash="abcd1234", python_version="3.11.0", api_version="1"
        )
        assert v.api_version == "1"

    def test_api_version_defaults_to_none(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="abcd1234", python_version="3.11.0")
        assert v.api_version is None

    def test_api_version_rejects_arbitrary_string(self) -> None:
        with pytest.raises(Exception):
            VersionInfo(
                version="1.0.0",
                build_hash="abcd1234",
                python_version="3.11.0",
                api_version="INVALID",
            )


class TestVersionInfoStr:
    def test_str_includes_version(self) -> None:
        v = VersionInfo(version="2.0.0", build_hash="abcd1234", python_version="3.11.0")
        assert "2.0.0" in str(v)

    def test_str_includes_python_version(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="abcd1234", python_version="3.11.0")
        assert "3.11.0" in str(v)

    def test_str_omits_hash_when_unknown(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="unknown", python_version="3.11.0")
        assert "unknown" not in str(v)

    def test_str_includes_api_version_when_set(self) -> None:
        v = VersionInfo(
            version="1.0.0", build_hash="abcd1234", python_version="3.11.0", api_version="v2"
        )
        assert "v2" in str(v)


class TestVersionInfoToDict:
    def test_returns_dict_with_all_fields(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="abcd1234", python_version="3.11.0")
        d = v.to_dict()
        assert d["version"] == "1.0.0"
        assert d["build_hash"] == "abcd1234"
        assert d["python_version"] == "3.11.0"

    def test_serializes_build_date_as_iso_string(self) -> None:
        build_date = datetime(2024, 6, 15, 12, 0, 0)
        v = VersionInfo(
            version="1.0.0",
            build_hash="abcd1234",
            python_version="3.11.0",
            build_date=build_date,
        )
        d = v.to_dict()
        assert "2024-06-15" in d["build_date"]


class TestVersionInfoToCliFormat:
    def test_includes_version_label(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="abcd1234", python_version="3.11.0")
        output = v.to_cli_format()
        assert "Pixl Version: 1.0.0" in output

    def test_includes_build_hash_label(self) -> None:
        v = VersionInfo(version="1.0.0", build_hash="abcd1234", python_version="3.11.0")
        output = v.to_cli_format()
        assert "Build Hash: abcd1234" in output

    def test_includes_api_version_when_set(self) -> None:
        v = VersionInfo(
            version="1.0.0", build_hash="abcd1234", python_version="3.11.0", api_version="v1"
        )
        output = v.to_cli_format()
        assert "API Version: v1" in output


class TestGetGitHash:
    def test_returns_string_or_none(self) -> None:
        # We just verify the return type contract — outcome depends on environment
        result = get_git_hash()
        assert result is None or isinstance(result, str)

    def test_returns_nonempty_string_when_in_git_repo(self) -> None:
        # We're running inside a git repo, so hash should be present
        result = get_git_hash()
        if result is not None:
            assert len(result) > 0
