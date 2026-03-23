import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """In-process publish/subscribe event bus for real-time event distribution."""

    def __init__(self) -> None:
        self._subscribers: list[tuple[str | None, Callable[..., Any]]] = []
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[..., Any], event_type: str | None = None) -> None:
        """Register a listener. If event_type is None, receives all events."""
        with self._lock:
            self._subscribers.append((event_type, callback))

    def unsubscribe(self, callback: Callable[..., Any]) -> None:
        """Remove all subscriptions for a given callback."""
        with self._lock:
            self._subscribers = [(et, cb) for et, cb in self._subscribers if cb is not callback]

    def publish(self, event: Any) -> None:
        """Publish an event to all matching subscribers.

        An event is any object with an ``event_type`` attribute (string).
        Subscriber errors are logged and never propagate to the publisher.
        """
        event_type: str = getattr(event, "event_type", "")
        with self._lock:
            snapshot = list(self._subscribers)

        for filter_type, callback in snapshot:
            if filter_type is not None and filter_type != event_type:
                continue
            try:
                callback(event)
            except Exception:
                logger.exception(
                    "Subscriber %r failed handling event type %r",
                    callback,
                    event_type,
                )

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)
