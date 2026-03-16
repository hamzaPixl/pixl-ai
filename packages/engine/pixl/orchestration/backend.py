"""ExecutionBackend protocol — the core abstraction for running agent sessions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pixl_sandbox.models import SandboxEvent


@dataclass(frozen=True)
class ExecutionConfig:
    """Configuration passed to any backend for a single execution."""

    project_id: str = ""
    git_url: str = ""
    session_id: str | None = None
    timeout: int = 1800
    long_running: bool = False


# ExecutionEvent is now an alias for SandboxEvent — same shape, no wrapper needed.
ExecutionEvent = SandboxEvent


@runtime_checkable
class ExecutionBackend(Protocol):
    """Protocol for executing agent prompts in Daytona sandboxes."""

    async def execute(
        self,
        prompt: str,
        config: ExecutionConfig,
    ) -> AsyncIterator[ExecutionEvent]:
        """Execute a prompt and yield structured events."""
        ...

    async def cancel(self, session_id: str) -> None:
        """Cancel a running execution."""
        ...
