"""Lazy-loading Click group for fast CLI startup.

Defers command module imports until the command is actually invoked,
which is critical for hooks that run on every tool call.
"""

from __future__ import annotations

import importlib
from typing import Any

import click


class LazyGroup(click.Group):
    """Click group that lazily imports command modules on first use."""

    def __init__(
        self,
        *args: Any,
        lazy_subcommands: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._lazy_subcommands: dict[str, str] = lazy_subcommands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_subcommands.keys())
        return base + lazy

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name in self._lazy_subcommands:
            return self._load_command(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _load_command(self, cmd_name: str) -> click.Command:
        module_path = self._lazy_subcommands[cmd_name]
        module = importlib.import_module(module_path)
        # Convention: each command module exposes a click group/command
        # with the same name as the module (e.g., knowledge.py -> knowledge)
        attr_name = cmd_name.replace("-", "_")
        return getattr(module, attr_name)
