"""SDK options builder with hooks and advanced features.

This module provides a centralized way to build ClaudeAgentOptions with:
- Resume capability for failed sessions
"""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Literal

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, HookCallback, HookMatcher
from claude_agent_sdk import types as sdk_types
from claude_agent_sdk.types import HookContext, HookJSONOutput

from pixl.agents.constants import DEFAULT_TOOLS

# Optional hooks subsystem — gracefully degrade if not yet extracted.
try:
    from pixl.agents.hooks import (
        HooksDict,
        create_default_registry,
        create_sdk_hooks_from_registry,
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
    ThinkingConfig = ThinkingConfigAdaptive | ThinkingConfigEnabled | ThinkingConfigDisabled

def _build_thinking_config(kind: str, budget_tokens: int | None = None) -> ThinkingConfig:
    if ThinkingConfigAdaptive is None:
        payload = {"type": kind}
        if budget_tokens is not None:
            payload["budget_tokens"] = budget_tokens
        return payload

    if kind == "adaptive":
        return ThinkingConfigAdaptive(type="adaptive")
    if kind == "enabled":
        return ThinkingConfigEnabled(
            type="enabled", budget_tokens=32_000 if budget_tokens is None else budget_tokens
        )
    if kind == "disabled":
        return ThinkingConfigDisabled(type="disabled")
    raise ValueError(f"Unknown thinking kind: {kind!r}")

def resolve_thinking_config(
    spec: "str | dict[str, Any] | ThinkingConfig | None",
) -> ThinkingConfig | None:
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
    system_prompt: str | None = None,
    max_budget_usd: float | None = None,
    fallback_model: str | None = None,
    output_format: dict[str, Any] | None = None,
    fork_session: bool = False,
    thinking: "str | dict[str, Any] | ThinkingConfig | None" = None,
    effort: "Literal['low', 'medium', 'high', 'max'] | None" = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for plugin-delegated sessions."""
    # Default to DEFAULT_TOOLS if not specified
    if allowed_tools is None:
        allowed_tools = list(DEFAULT_TOOLS)

    if extra_tools:
        for tool in extra_tools:
            if tool not in allowed_tools:
                allowed_tools.append(tool)

    hooks: HooksDict = {}

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

    options = ClaudeAgentOptions(
        allowed_tools=allowed_tools,
        permission_mode="bypassPermissions",
        cwd=str(cwd or project_path),
        max_turns=max_turns,
        hooks=hooks if hooks else None,
        setting_sources=["user", "project"],
        agents=agents,
        extra_args={"debug-to-stderr": None},
    )

    if resume_session_id:
        options.resume = resume_session_id
    if continue_conversation:
        options.continue_conversation = True
    if model:
        options.model = model

    # System prompt — keeps user prompt clean
    if system_prompt:
        options.system_prompt = system_prompt

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

    return hook
