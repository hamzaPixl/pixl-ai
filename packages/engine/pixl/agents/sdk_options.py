"""SDK options builder with hooks and advanced features.

This module provides a centralized way to build ClaudeAgentOptions with:
- Resume capability for failed sessions
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, HookCallback, HookMatcher
from claude_agent_sdk import types as sdk_types
from claude_agent_sdk.types import HookContext, HookJSONOutput

from pixl.agents.constants import DEFAULT_TOOLS

if TYPE_CHECKING:
    from typing import Literal


def _resolve_crew_plugin_path() -> str | None:
    """Resolve crew plugin path for programmatic loading.

    Resolution chain (mirrors pixl_cli.crew.get_crew_root):
    1. PIXL_CREW_ROOT env var
    2. Monorepo: packages/crew/ (sibling of packages/engine/)
    3. Bundled: _crew/ inside this package
    """
    # 1. Env override
    env_root = os.environ.get("PIXL_CREW_ROOT")
    if env_root and Path(env_root).is_dir():
        plugin_json = Path(env_root) / ".claude-plugin" / "plugin.json"
        if plugin_json.is_file():
            return env_root

    # 2. Monorepo layout: this file is packages/engine/pixl/agents/sdk_options.py
    engine_pkg = Path(__file__).resolve().parent.parent.parent  # packages/engine/
    crew_dir = engine_pkg.parent / "crew"
    if (crew_dir / ".claude-plugin" / "plugin.json").is_file():
        return str(crew_dir)

    # 3. Bundled in wheel
    bundled = Path(__file__).resolve().parent.parent / "_crew"
    if (bundled / ".claude-plugin" / "plugin.json").is_file():
        return str(bundled)

    return None


# Optional hooks subsystem — gracefully degrade if not yet extracted.
try:
    from pixl.agents.hooks import (
        HooksDict,  # type: ignore[attr-defined]
        create_default_registry,  # type: ignore[attr-defined]
        create_sdk_hooks_from_registry,  # type: ignore[attr-defined]
    )

    _HOOKS_AVAILABLE = True
except ImportError:
    _HOOKS_AVAILABLE = False

    HooksDict = dict  # type: ignore[misc,assignment]

    def create_default_registry() -> Any:  # type: ignore[misc]
        return None

    def create_sdk_hooks_from_registry(registry: Any) -> dict:  # type: ignore[misc]
        return {}


ThinkingConfigAdaptive = getattr(sdk_types, "ThinkingConfigAdaptive", None)
ThinkingConfigDisabled = getattr(sdk_types, "ThinkingConfigDisabled", None)
ThinkingConfigEnabled = getattr(sdk_types, "ThinkingConfigEnabled", None)

ThinkingConfig = dict[str, Any]
if (
    ThinkingConfigAdaptive is not None
    and ThinkingConfigEnabled is not None
    and ThinkingConfigDisabled is not None
):
    ThinkingConfig = ThinkingConfigAdaptive | ThinkingConfigEnabled | ThinkingConfigDisabled  # type: ignore[reportInvalidTypeForm]


def _build_thinking_config(kind: str, budget_tokens: int | None = None) -> Any:
    if ThinkingConfigAdaptive is None:
        payload: dict[str, Any] = {"type": kind}
        if budget_tokens is not None:
            payload["budget_tokens"] = budget_tokens
        return payload

    if kind == "adaptive":
        return ThinkingConfigAdaptive(type="adaptive")  # type: ignore[reportInvalidTypeForm]
    if kind == "enabled":
        return ThinkingConfigEnabled(  # type: ignore[reportInvalidTypeForm]
            type="enabled", budget_tokens=32_000 if budget_tokens is None else budget_tokens
        )
    if kind == "disabled":
        return ThinkingConfigDisabled(type="disabled")  # type: ignore[reportInvalidTypeForm]
    raise ValueError(f"Unknown thinking kind: {kind!r}")


def resolve_thinking_config(
    spec: "str | dict[str, Any] | Any | None",
) -> Any:
    """Convert a thinking spec to a typed SDK config.

    Accepts:
    - None → None
    - "adaptive" / "enabled" / "disabled" → corresponding typed config
    - dict with "type" key → typed config (budget_tokens for "enabled")
    """
    if spec is None:
        return None

    # String shorthand
    if isinstance(spec, str):
        if spec == "adaptive":
            return _build_thinking_config("adaptive")
        if spec == "enabled":
            return _build_thinking_config("enabled", budget_tokens=32_000)
        if spec == "disabled":
            return _build_thinking_config("disabled")
        msg = f"Unknown thinking spec: {spec!r}"
        raise ValueError(msg)

    # Dict form (from YAML or already a TypedDict)
    if isinstance(spec, dict):
        kind = spec.get("type", "adaptive")
        if kind == "adaptive":
            return _build_thinking_config("adaptive")
        if kind == "enabled":
            raw_budget: Any = spec.get("budget_tokens", 32_000)
            budget = int(raw_budget)
            return _build_thinking_config("enabled", budget_tokens=budget)
        if kind == "disabled":
            return _build_thinking_config("disabled")
        msg = f"Unknown thinking type in dict: {kind!r}"
        raise ValueError(msg)

    return None


def _build_crew_system_prompt(crew_path: str | Path) -> str | None:
    """Build a system prompt listing available crew skills from the plugin directory.

    Reads skill names dynamically from the crew's skills/ directory so the
    prompt stays in sync as skills are added or removed.
    """
    crew_path = Path(crew_path) if not isinstance(crew_path, Path) else crew_path
    skills_dir = crew_path / "skills"
    if not skills_dir.is_dir():
        return None
    skills = sorted(
        d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    )
    if not skills:
        return None
    skill_list = ", ".join(f"/{s}" for s in skills)
    return (
        "You have access to pixl-crew skills via the Skill tool. "
        "Prefer invoking a skill over building from scratch when the task matches.\n\n"
        f"Available skills: {skill_list}"
    )


def build_sdk_options(
    *,
    project_path: Path,
    allowed_tools: list[str] | None = None,
    extra_tools: list[str] | None = None,
    agents: dict[str, AgentDefinition] | None = None,
    max_turns: int = 50,
    model: str | None = None,
    cwd: str | Path | None = None,
    resume_session_id: str | None = None,
    continue_conversation: bool = False,
    enable_safety_hooks: bool = True,
    on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
    on_post_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
    system_prompt: str | None = None,
    max_budget_usd: float | None = None,
    fallback_model: str | None = None,
    output_format: dict[str, Any] | None = None,
    fork_session: bool = False,
    thinking: "str | dict[str, Any] | Any | None" = None,
    effort: "Literal['low', 'medium', 'high', 'max'] | None" = None,
    load_crew_plugin: bool = True,
    agent_registry: Any = None,
    crew_hook_profile: str = "standard",
    enable_todo_tracking: bool = False,
    todo_emit_event: Callable[..., Any] | None = None,
    todo_session_id: str | None = None,
    todo_node_id: str | None = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for plugin-delegated sessions."""
    # Default to DEFAULT_TOOLS if not specified
    if allowed_tools is None:
        allowed_tools = list(DEFAULT_TOOLS)

    if extra_tools:
        for tool in extra_tools:
            if tool not in allowed_tools:
                allowed_tools.append(tool)

    hooks: HooksDict = {}  # type: ignore[reportInvalidTypeForm]

    # Wire orchestration hooks (tool budget, context window, output truncation)
    if enable_safety_hooks and _HOOKS_AVAILABLE:
        registry = create_default_registry()
        hooks = create_sdk_hooks_from_registry(registry)

    additional_pre_hooks: list[HookCallback] = []

    if on_tool_call:
        additional_pre_hooks.append(_create_tool_callback_hook(on_tool_call))

    if additional_pre_hooks:
        if "PreToolUse" in hooks:
            existing_hooks = hooks["PreToolUse"][0].hooks
            hooks["PreToolUse"] = [
                HookMatcher(matcher=None, hooks=list(existing_hooks) + additional_pre_hooks)
            ]
        else:
            hooks["PreToolUse"] = [HookMatcher(matcher=None, hooks=additional_pre_hooks)]

    # PostToolUse callback (e.g., TodoWrite bridge)
    additional_post_hooks: list[HookCallback] = []
    if on_post_tool_call:
        additional_post_hooks.append(_create_tool_callback_hook(on_post_tool_call))

    # Wire TodoWrite bridge automatically when event emitter is provided (GAP-05)
    if enable_todo_tracking and todo_emit_event is not None:
        from pixl.agents.hooks.todo_bridge import create_todo_tracking_callback

        todo_callback = create_todo_tracking_callback(
            emit_event=todo_emit_event,
            session_id=todo_session_id,
            node_id=todo_node_id,
        )
        additional_post_hooks.append(_create_tool_callback_hook(todo_callback))

    if additional_post_hooks:
        if "PostToolUse" in hooks:
            existing_post = hooks["PostToolUse"][0].hooks
            hooks["PostToolUse"] = [
                HookMatcher(matcher=None, hooks=list(existing_post) + additional_post_hooks)
            ]
        else:
            hooks["PostToolUse"] = [HookMatcher(matcher=None, hooks=additional_post_hooks)]

    # Resolve crew path once for both hooks and plugin loading
    crew_path = _resolve_crew_plugin_path() if load_crew_plugin else None

    # Bridge crew shell hooks to SDK callbacks (GAP-03)
    if crew_path:
        try:
            from pixl.agents.hooks.crew_bridge import load_crew_hooks

            crew_hooks = load_crew_hooks(Path(crew_path), profile=crew_hook_profile)
            for event_name, matchers in crew_hooks.items():
                existing = hooks.get(event_name, [])
                hooks[event_name] = existing + matchers
        except Exception:
            pass  # Graceful degradation — crew hooks are optional

    # Resolve agents from registry if not explicitly provided (GAP-02)
    if agents is None and agent_registry is not None:
        agents = agent_registry.get_all_definitions()

    # Resolve crew plugin for programmatic loading (GAP-01)
    plugins: list[dict[str, str]] | None = None
    if crew_path:
        plugins = [{"type": "local", "path": crew_path}]

    # Pass hook profile to the Claude Code child process via env
    # so plugin-loaded hooks also respect the profile (SDK-bridged hooks
    # are already filtered by crew_hook_profile above).
    sdk_env: dict[str, str] = {}
    if crew_hook_profile != "standard":
        sdk_env["PIXL_HOOK_PROFILE"] = crew_hook_profile

    # Redirect Claude Code's stderr to a log file instead of /dev/null.
    # SDK sessions emit AbortError stack traces on teardown (InboxPoller,
    # nudge hooks) which corrupt the terminal. We capture them to a log file
    # for debugging instead of discarding silently.
    _sdk_log_dir = Path(project_path or ".") / ".pixl"
    _sdk_log_dir.mkdir(parents=True, exist_ok=True)
    _stderr_log = open(_sdk_log_dir / "sdk-stderr.log", "a")  # noqa: SIM115

    options = ClaudeAgentOptions(
        allowed_tools=allowed_tools,
        permission_mode="bypassPermissions",
        cwd=str(cwd or project_path),
        max_turns=max_turns,
        hooks=hooks if hooks else None,
        setting_sources=["user", "project"],
        agents=agents,
        plugins=plugins,  # type: ignore[arg-type]
        env=sdk_env,
        debug_stderr=_stderr_log,
    )

    if resume_session_id:
        options.resume = resume_session_id
    if continue_conversation:
        options.continue_conversation = True
    if model:
        options.model = model

    # System prompt — keeps user prompt clean.
    # When no explicit prompt is given, inject crew skill awareness so the
    # agent knows which skills are available and prefers them over ad-hoc code.
    if system_prompt:
        options.system_prompt = system_prompt
    elif crew_path:
        crew_prompt = _build_crew_system_prompt(crew_path)
        if crew_prompt:
            options.system_prompt = crew_prompt

    # Cost safety net per query
    if max_budget_usd is not None:
        options.max_budget_usd = max_budget_usd

    # Fallback model on transient errors
    if fallback_model:
        options.fallback_model = fallback_model

    # Native structured output format
    if output_format:
        options.output_format = output_format

    # Fork from a prior session
    if fork_session:
        options.fork_session = True

    # Extended thinking configuration (SDK v0.1.37+)
    resolved_thinking = resolve_thinking_config(thinking)
    if resolved_thinking is not None:
        if hasattr(options, "thinking"):
            options.thinking = resolved_thinking
        elif isinstance(resolved_thinking, dict):
            if resolved_thinking.get("type") == "enabled":
                budget_val = resolved_thinking.get("budget_tokens")
                if budget_val is not None:
                    options.max_thinking_tokens = int(budget_val)
            elif resolved_thinking.get("type") == "disabled":
                options.max_thinking_tokens = 0

    # Effort level (SDK v0.1.37+)
    if effort is not None and hasattr(options, "effort"):
        options.effort = effort

    return options


def _create_tool_callback_hook(
    callback: Callable[[str, dict[str, Any]], None],
) -> HookCallback:
    """Create a hook that calls a callback when a tool is used."""

    async def hook(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookJSONOutput:
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        callback(tool_name, tool_input)
        return {}

    return hook  # type: ignore[return-value]
