"""Thread exception hook for uncaught errors in background threads."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


def install_thread_excepthook() -> None:
    """Install a ``threading.excepthook`` that logs uncaught thread exceptions."""

    def _hook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit:
            return
        logger.error(
            "Uncaught exception in thread '%s'",
            args.thread.name if args.thread else "<unknown>",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),  # type: ignore[arg-type]
        )

    threading.excepthook = _hook
