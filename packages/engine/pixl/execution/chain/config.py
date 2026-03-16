"""Chain execution configuration load/save."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixl.storage.db.connection import PixlDB

_CHAIN_CONFIG_PREFIX = "chain_exec:"


def _chain_exec_key(chain_id: str) -> str:
    return f"{_CHAIN_CONFIG_PREFIX}{chain_id}"


def load_chain_exec_config(db: PixlDB, chain_id: str) -> dict[str, Any]:
    raw = db.get_config(_chain_exec_key(chain_id), default=None)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def save_chain_exec_config(
    db: PixlDB,
    chain_id: str,
    *,
    workflow_id: str,
    skip_approval: bool,
    base_remote: str = "origin",
    base_branch: str | None = None,
    base_ref: str | None = None,
    pr_automation_enabled: bool = True,
    merge_method: str = "squash",
) -> None:
    payload = {
        "workflow_id": workflow_id,
        "skip_approval": bool(skip_approval),
        "base_remote": base_remote,
        "base_branch": base_branch,
        "base_ref": base_ref,
        "pr_automation": bool(pr_automation_enabled),
        "merge_method": merge_method,
        "updated_at": datetime.now().isoformat(),
    }
    db.set_config(_chain_exec_key(chain_id), json.dumps(payload, sort_keys=True))


def patch_chain_exec_config(db: PixlDB, chain_id: str, *, updates: dict[str, Any]) -> None:
    cfg = load_chain_exec_config(db, chain_id)
    cfg.update(updates or {})
    cfg["updated_at"] = datetime.now().isoformat()
    db.set_config(_chain_exec_key(chain_id), json.dumps(cfg, sort_keys=True))
