"""Execution backend resolution."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pixl.storage.config_store import ConfigStore

logger = logging.getLogger(__name__)

DEFAULT_EXECUTION_BACKEND = "sandbox"


def resolve_execution_backend(project_path: Path) -> str:
    """Resolve execution backend (sandbox or sdk)."""
    env = os.getenv("PIXL_EXECUTION_BACKEND")
    if env:
        return env.strip().lower()

    cfg = ConfigStore(project_path).load()
    backend = (cfg.execution_backend or DEFAULT_EXECUTION_BACKEND).strip().lower()
    return backend
