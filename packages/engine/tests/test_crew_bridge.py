"""Tests for crew hook bridge — wraps shell hooks as SDK HookCallback functions."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pixl.agents.hooks.crew_bridge import (
    _create_crew_hook,
    _run_shell_hook,
    load_crew_hooks,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def crew_root(tmp_path: Path) -> Path:
    """Create a minimal crew directory with hooks structure."""
    crew = tmp_path / "crew"
    (crew / ".claude-plugin").mkdir(parents=True)
    (crew / ".claude-plugin" / "plugin.json").write_text('{"name": "test-crew"}')
    (crew / "hooks" / "scripts").mkdir(parents=True)
    return crew


@pytest.fixture()
def hooks_json_path(crew_root: Path) -> Path:
    return crew_root / "hooks" / "hooks.json"


@pytest.fixture()
def allow_script(crew_root: Path) -> Path:
    """A hook script that reads stdin and exits 0 (allow)."""
    script = crew_root / "hooks" / "scripts" / "allow.sh"
    script.write_text("#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n")
    script.chmod(0o755)
    return script


@pytest.fixture()
def block_script(crew_root: Path) -> Path:
    """A hook script that reads stdin and exits 2 (block)."""
    script = crew_root / "hooks" / "scripts" / "block.sh"
    script.write_text(
        "#!/usr/bin/env bash\ncat > /dev/null\n"
        "echo '{\"decision\":\"block\",\"reason\":\"test\"}'\n"
        "exit 2\n"
    )
    script.chmod(0o755)
    return script


@pytest.fixture()
def echo_script(crew_root: Path) -> Path:
    """A hook script that echoes JSON output to stdout."""
    script = crew_root / "hooks" / "scripts" / "echo-json.sh"
    script.write_text(
        "#!/usr/bin/env bash\ncat > /dev/null\n"
        "echo '{\"decision\":\"block\",\"reason\":\"blocked by test\"}'\n"
    )
    script.chmod(0o755)
    return script


# ── _run_shell_hook ───────────────────────────────────────────────────────


class TestRunShellHook:

    @pytest.mark.asyncio()
    async def test_returns_empty_dict_on_success_no_output(
        self, allow_script: Path
    ) -> None:
        result = await _run_shell_hook(str(allow_script), {"tool_name": "Bash"})
        assert result == {}

    @pytest.mark.asyncio()
    async def test_parses_json_stdout(self, echo_script: Path) -> None:
        result = await _run_shell_hook(str(echo_script), {"tool_name": "Write"})
        assert result == {"decision": "block", "reason": "blocked by test"}

    @pytest.mark.asyncio()
    async def test_returns_empty_dict_on_nonzero_exit(
        self, block_script: Path
    ) -> None:
        result = await _run_shell_hook(str(block_script), {"tool_name": "Bash"})
        # Exit code 2 means non-zero, so stdout is not parsed
        assert result == {}

    @pytest.mark.asyncio()
    async def test_returns_empty_dict_on_missing_script(self) -> None:
        result = await _run_shell_hook(
            "/nonexistent/script.sh", {"tool_name": "Bash"}
        )
        assert result == {}

    @pytest.mark.asyncio()
    async def test_passes_input_as_stdin(self, crew_root: Path) -> None:
        """The script receives hook input data as JSON on stdin."""
        script = crew_root / "hooks" / "scripts" / "echo-stdin.sh"
        script.write_text("#!/usr/bin/env bash\ncat\n")
        script.chmod(0o755)

        input_data = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        result = await _run_shell_hook(str(script), input_data)
        assert result["tool_name"] == "Bash"
        assert result["tool_input"]["command"] == "ls"


# ── _create_crew_hook ─────────────────────────────────────────────────────


class TestCreateCrewHook:

    @pytest.mark.asyncio()
    async def test_returns_callable_hook(self, echo_script: Path) -> None:
        hook = _create_crew_hook(str(echo_script))
        assert callable(hook)

    @pytest.mark.asyncio()
    async def test_hook_delegates_to_script(self, echo_script: Path) -> None:
        hook = _create_crew_hook(str(echo_script))
        mock_context = MagicMock()
        result = await hook({"tool_name": "Write"}, "tool-123", mock_context)
        assert result.get("decision") == "block"


# ── load_crew_hooks ───────────────────────────────────────────────────────


class TestLoadCrewHooks:

    def test_returns_empty_dict_when_no_hooks_json(
        self, crew_root: Path
    ) -> None:
        result = load_crew_hooks(crew_root)
        assert result == {}

    def test_loads_pre_tool_use_hooks(
        self,
        crew_root: Path,
        hooks_json_path: Path,
        allow_script: Path,
    ) -> None:
        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Bash",
                    "hooks": [{
                        "type": "command",
                        "command": f"bash {allow_script}",
                    }],
                }],
            },
        }))
        result = load_crew_hooks(crew_root)
        assert "PreToolUse" in result
        assert len(result["PreToolUse"]) == 1
        assert result["PreToolUse"][0].matcher == "Bash"
        assert len(result["PreToolUse"][0].hooks) == 1

    def test_loads_multiple_events(
        self,
        crew_root: Path,
        hooks_json_path: Path,
        allow_script: Path,
    ) -> None:
        cmd = f"bash {allow_script}"
        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": cmd}],
                }],
                "PostToolUse": [{
                    "matcher": "Write|Edit",
                    "hooks": [{"type": "command", "command": cmd}],
                }],
            },
        }))
        result = load_crew_hooks(crew_root)
        assert "PreToolUse" in result
        assert "PostToolUse" in result

    def test_skips_prompt_type_hooks(
        self, crew_root: Path, hooks_json_path: Path
    ) -> None:
        """Only command-type hooks are bridged; prompt-type hooks are skipped."""
        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Write|Edit",
                    "hooks": [
                        {"type": "prompt", "prompt": "Check the tool input..."},
                    ],
                }],
            },
        }))
        result = load_crew_hooks(crew_root)
        # Prompt hooks are skipped; empty matchers are not added
        assert "PreToolUse" not in result

    def test_skips_unsupported_events(
        self,
        crew_root: Path,
        hooks_json_path: Path,
        allow_script: Path,
    ) -> None:
        """SessionStart is not an SDK hook event -- should be skipped."""
        cmd = f"bash {allow_script}"
        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "SessionStart": [{
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": cmd}],
                }],
                "PreToolUse": [{
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": cmd}],
                }],
            },
        }))
        result = load_crew_hooks(crew_root)
        assert "SessionStart" not in result
        assert "PreToolUse" in result

    def test_profile_filtering_minimal(
        self, crew_root: Path, hooks_json_path: Path
    ) -> None:
        """Minimal profile only loads critical hooks."""
        scripts = {}
        for name in ("critical", "quality"):
            s = crew_root / "hooks" / "scripts" / f"{name}.sh"
            s.write_text("#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n")
            s.chmod(0o755)
            scripts[name] = s

        critical_cmd = (
            "bash scripts/run-with-flags.sh block-destructive critical "
            f"{scripts['critical']}"
        )
        quality_cmd = (
            "bash scripts/run-with-flags.sh tdd-check quality "
            f"{scripts['quality']}"
        )
        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": critical_cmd},
                        {"type": "command", "command": quality_cmd},
                    ],
                }],
            },
        }))
        result = load_crew_hooks(crew_root, profile="minimal")
        assert "PreToolUse" in result
        total_hooks = sum(len(m.hooks) for m in result["PreToolUse"])
        assert total_hooks == 1

    def test_profile_filtering_standard(
        self, crew_root: Path, hooks_json_path: Path
    ) -> None:
        """Standard profile loads critical + quality, but not advisory."""
        scripts = {}
        for name in ("critical", "advisory"):
            s = crew_root / "hooks" / "scripts" / f"{name}.sh"
            s.write_text("#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n")
            s.chmod(0o755)
            scripts[name] = s

        critical_cmd = (
            "bash scripts/run-with-flags.sh observe critical "
            f"{scripts['critical']}"
        )
        advisory_cmd = (
            "bash scripts/run-with-flags.sh suggest advisory "
            f"{scripts['advisory']}"
        )
        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PostToolUse": [{
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": critical_cmd},
                        {"type": "command", "command": advisory_cmd},
                    ],
                }],
            },
        }))
        result = load_crew_hooks(crew_root, profile="standard")
        assert "PostToolUse" in result
        total_hooks = sum(len(m.hooks) for m in result["PostToolUse"])
        assert total_hooks == 1

    def test_profile_filtering_strict_loads_all(
        self, crew_root: Path, hooks_json_path: Path
    ) -> None:
        """Strict profile loads all hooks."""
        scripts_dir = crew_root / "hooks" / "scripts"
        for name in ("critical", "quality", "advisory"):
            s = scripts_dir / f"{name}.sh"
            s.write_text("#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n")
            s.chmod(0o755)

        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "bash scripts/run-with-flags.sh block"
                                f" critical {scripts_dir}/critical.sh"
                            ),
                        },
                        {
                            "type": "command",
                            "command": (
                                "bash scripts/run-with-flags.sh tdd"
                                f" quality {scripts_dir}/quality.sh"
                            ),
                        },
                        {
                            "type": "command",
                            "command": (
                                "bash scripts/run-with-flags.sh suggest"
                                f" advisory {scripts_dir}/advisory.sh"
                            ),
                        },
                    ],
                }],
            },
        }))
        result = load_crew_hooks(crew_root, profile="strict")
        total_hooks = sum(len(m.hooks) for m in result["PreToolUse"])
        assert total_hooks == 3

    def test_timeout_propagated(
        self,
        crew_root: Path,
        hooks_json_path: Path,
        allow_script: Path,
    ) -> None:
        """Timeout from hooks.json is propagated to HookMatcher."""
        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "Stop": [{
                    "matcher": "*",
                    "hooks": [{
                        "type": "command",
                        "command": f"bash {allow_script}",
                        "timeout": 30,
                    }],
                }],
            },
        }))
        result = load_crew_hooks(crew_root)
        assert "Stop" in result
        assert result["Stop"][0].timeout == 30

    def test_multiple_hooks_per_matcher(
        self, crew_root: Path, hooks_json_path: Path
    ) -> None:
        """Multiple command hooks under one matcher produce multiple callbacks."""
        scripts_dir = crew_root / "hooks" / "scripts"
        for name in ("hook-a", "hook-b"):
            s = scripts_dir / f"{name}.sh"
            s.write_text("#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n")
            s.chmod(0o755)

        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"bash {scripts_dir}/hook-a.sh",
                        },
                        {
                            "type": "command",
                            "command": f"bash {scripts_dir}/hook-b.sh",
                        },
                    ],
                }],
            },
        }))
        result = load_crew_hooks(crew_root)
        assert len(result["PreToolUse"]) == 1
        assert len(result["PreToolUse"][0].hooks) == 2

    def test_resolves_script_from_run_with_flags_command(
        self, crew_root: Path, hooks_json_path: Path
    ) -> None:
        """Commands using run-with-flags.sh resolve to the actual script."""
        actual_script = crew_root / "hooks" / "scripts" / "block-destructive.sh"
        actual_script.write_text(
            "#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n"
        )
        actual_script.chmod(0o755)

        hooks_json_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Bash",
                    "hooks": [{
                        "type": "command",
                        "command": (
                            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                            "run-with-flags.sh block-destructive critical "
                            "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                            "block-destructive.sh"
                        ),
                    }],
                }],
            },
        }))
        result = load_crew_hooks(crew_root)
        assert "PreToolUse" in result
        assert len(result["PreToolUse"][0].hooks) == 1
