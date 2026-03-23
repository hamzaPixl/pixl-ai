"""Bridge crew shell hooks to SDK HookCallback functions.

Crew hooks are bash scripts that receive JSON on stdin and communicate via:
- Exit code 0: allow (success)
- Exit code 2: block
- stdout: JSON output (parsed if exit 0 and non-empty)

This module parses hooks.json, resolves script paths, applies profile-based
filtering (minimal/standard/strict), and produces SDK HookMatcher objects.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from claude_agent_sdk import HookCallback, HookMatcher
from claude_agent_sdk.types import HookContext, HookJSONOutput

logger = logging.getLogger(__name__)

# SDK hook events that can be bridged. SessionStart is handled separately
# by the plugin system and is not an SDK HookMatcher event.
_SUPPORTED_EVENTS = frozenset({
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "Notification",
})

# Profile rank for filtering — higher rank includes all lower levels.
_PROFILE_RANK = {"minimal": 0, "standard": 1, "strict": 2}

# Hook level rank — must meet or exceed the profile rank to run.
_LEVEL_RANK = {"critical": 0, "quality": 1, "advisory": 2}


async def _run_shell_hook(script_path: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute a crew shell hook script and parse its JSON output.

    The script receives input_data as JSON on stdin. Only stdout from
    a successful (exit 0) execution is parsed as JSON.

    Returns:
        Parsed JSON dict on success, empty dict on failure or non-JSON output.
    """
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            ["bash", script_path],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        logger.debug("Hook %s failed: %s", script_path, exc)
    return {}


def _create_crew_hook(script_path: str) -> HookCallback:
    """Create an SDK HookCallback that delegates to a crew shell script."""

    async def hook(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookJSONOutput:
        return await _run_shell_hook(script_path, input_data)

    return hook


def _extract_profile_level(command: str) -> str | None:
    """Extract the hook profile level from a run-with-flags.sh command.

    Format: bash .../run-with-flags.sh <hook-id> <level> <script> [args...]

    Returns:
        The level string ("critical", "quality", "advisory") or None if
        the command does not use run-with-flags.sh.
    """
    parts = command.split()
    for i, part in enumerate(parts):
        if part.endswith("run-with-flags.sh") and i + 2 < len(parts):
            # parts[i+1] = hook-id, parts[i+2] = level
            return parts[i + 2]
    return None


def _resolve_script_path(command: str, scripts_dir: Path) -> Path | None:
    """Resolve the actual script path from a hook command string.

    Handles two patterns:
    1. Direct: "bash /path/to/script.sh" or "bash ${CLAUDE_PLUGIN_ROOT}/.../script.sh"
    2. run-with-flags.sh wrapper: "bash .../run-with-flags.sh <id> <level> <script>"

    For pattern 2, the actual script is the argument after the level.
    For both patterns, ${CLAUDE_PLUGIN_ROOT} is resolved to crew_root.
    """
    parts = command.split()

    # Find the actual script (last .sh argument, or the one after level in run-with-flags)
    script_part: str | None = None

    # Check if this uses run-with-flags.sh
    for i, part in enumerate(parts):
        if part.endswith("run-with-flags.sh") and i + 3 < len(parts):
            # The actual script is parts[i+3]
            script_part = parts[i + 3]
            break

    if script_part is None:
        # Direct command — find the last .sh argument
        for part in reversed(parts):
            if part.endswith(".sh"):
                script_part = part
                break

    if script_part is None:
        return None

    # Resolve ${CLAUDE_PLUGIN_ROOT} references
    if "${CLAUDE_PLUGIN_ROOT}" in script_part:
        # Extract just the filename and look in scripts_dir
        script_name = Path(script_part.split("/")[-1]).name
        candidate = scripts_dir / script_name
        if candidate.exists():
            return candidate
        return None

    # Absolute or relative path
    script_path = Path(script_part)
    if script_path.is_absolute() and script_path.exists():
        return script_path

    # Try resolving relative to scripts_dir
    candidate = scripts_dir / script_path.name
    if candidate.exists():
        return candidate

    return None


def _should_run(level: str | None, target_rank: int) -> bool:
    """Check if a hook at the given level should run for the target profile rank."""
    if level is None:
        # No run-with-flags wrapper — always include (direct commands)
        return True
    level_rank = _LEVEL_RANK.get(level, 1)  # default to quality
    return level_rank <= target_rank


def load_crew_hooks(crew_root: Path, profile: str = "standard") -> dict[str, list[HookMatcher]]:
    """Load crew hooks.json and build SDK hook matchers.

    Parses the crew plugin's hooks.json, resolves script paths, applies
    profile-based filtering, and returns a dict suitable for merging into
    the SDK hooks configuration.

    Args:
        crew_root: Path to the crew plugin directory.
        profile: Hook profile — "minimal", "standard", or "strict".

    Returns:
        Dict mapping hook event names to lists of HookMatcher objects.
    """
    hooks_json = crew_root / "hooks" / "hooks.json"
    if not hooks_json.exists():
        return {}

    try:
        config = json.loads(hooks_json.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.debug("Failed to parse hooks.json: %s", exc)
        return {}

    target_rank = _PROFILE_RANK.get(profile, 1)
    scripts_dir = crew_root / "hooks" / "scripts"
    sdk_hooks: dict[str, list[HookMatcher]] = {}

    hooks_section = config.get("hooks", {})

    for event_name, matchers in hooks_section.items():
        if event_name not in _SUPPORTED_EVENTS:
            continue

        if not isinstance(matchers, list):
            continue

        for matcher_entry in matchers:
            matcher_pattern = matcher_entry.get("matcher")
            hook_defs = matcher_entry.get("hooks", [])

            callbacks: list[HookCallback] = []
            max_timeout: float | None = None

            for hook_def in hook_defs:
                # Only bridge command-type hooks; skip prompt-type hooks
                if hook_def.get("type") != "command":
                    continue

                command = hook_def.get("command", "")
                if not command:
                    continue

                # Apply profile filtering
                level = _extract_profile_level(command)
                if not _should_run(level, target_rank):
                    continue

                # Resolve script path
                script_path = _resolve_script_path(command, scripts_dir)
                if script_path is None:
                    continue

                callbacks.append(_create_crew_hook(str(script_path)))

                # Track max timeout for the matcher
                hook_timeout = hook_def.get("timeout")
                if hook_timeout is not None:
                    if max_timeout is None or hook_timeout > max_timeout:
                        max_timeout = float(hook_timeout)

            if not callbacks:
                continue

            hook_matcher = HookMatcher(
                matcher=matcher_pattern,
                hooks=callbacks,
                timeout=max_timeout,
            )

            if event_name not in sdk_hooks:
                sdk_hooks[event_name] = []
            sdk_hooks[event_name].append(hook_matcher)

    return sdk_hooks
