"""Shared async-from-sync bridge.

Provides ``run_coroutine_sync`` for calling async code from synchronous
callers, even when an event loop is already running (e.g. inside FastAPI
BackgroundTasks).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any

# Module-level thread pool — avoids spawning a fresh thread per blocking call
# when an event loop is already running.
_coroutine_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def run_coroutine_sync(coro: Any) -> Any:
    """Run a coroutine from sync code, even if an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop in this thread — create one and run directly.
        return asyncio.run(coro)

    if loop.is_running():
        # The current thread owns a running loop (e.g. FastAPI BackgroundTask
        # running inside an async context).  We cannot call loop.run_until_complete()
        # here because the loop is already spinning, so we delegate to a
        # pooled thread with its own ephemeral event loop.
        future = _coroutine_pool.submit(asyncio.run, coro)
        return future.result()

    # Reuse it instead of spawning a thread.
    return loop.run_until_complete(coro)
