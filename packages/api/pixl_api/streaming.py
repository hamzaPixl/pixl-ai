"""SSE streaming helpers for bridging sync engine events to async responses.

The GraphExecutor runs synchronously in a background thread and pushes
events into an asyncio.Queue.  The async generator drains that queue
and yields SSE-formatted lines to the HTTP client.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

# Keepalive interval when no events are available (seconds).
_KEEPALIVE_TIMEOUT = 1.0


async def workflow_event_generator(
    event_queue: asyncio.Queue[dict],
    done_event: asyncio.Event,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events from *event_queue* until *done_event* is set.

    Sends periodic keepalive comments so proxies/browsers don't drop the
    connection.
    """
    while not done_event.is_set() or not event_queue.empty():
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=_KEEPALIVE_TIMEOUT)
            yield f"data: {json.dumps(event, default=str)}\n\n"
        except TimeoutError:
            yield ": keepalive\n\n"
        except Exception:
            logger.exception("Unexpected error in SSE generator")
            break

    # Terminal marker so the client knows the stream is complete.
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def create_sse_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    """Wrap an async SSE generator in a Starlette StreamingResponse."""
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
