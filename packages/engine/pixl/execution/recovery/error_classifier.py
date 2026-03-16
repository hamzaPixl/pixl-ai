"""Error classification and diff extraction utilities."""

from __future__ import annotations

import re
from typing import Any

from pixl.errors import (
    ContractError as PixlContractError,
)
from pixl.errors import (
    PixlError,
    ProviderError,
    StateError,
)
from pixl.errors import (
    TimeoutError as PixlTimeoutError,
)


def error_from_result(execution_result: dict[str, Any]) -> PixlError:
    """Build a typed PixlError from an execution_result dict.

    Used to feed the recovery policy when failures arrive as return
    values rather than exceptions.
    """
    error_msg = execution_result.get("error", "Unknown error")
    failure_kind = execution_result.get("failure_kind", "")
    error_type = execution_result.get("error_type", "")

    if error_type == "provider_error" or failure_kind == "provider":
        metadata = execution_result.get("error_metadata", {})
        return ProviderError(
            error_msg,
            http_status=metadata.get("http_status"),
            retry_after=metadata.get("retry_after"),
            provider=metadata.get("provider"),
            model=metadata.get("model"),
        )

    if error_type == "timeout_error" or failure_kind == "timeout":
        return PixlTimeoutError(error_msg)

    if error_type == "contract_error" or failure_kind == "contract_violation":
        metadata = execution_result.get("error_metadata", {})
        rule = metadata.get("rule") or failure_kind
        return PixlContractError(error_msg, rule=rule)

    if error_type == "state_error":
        return StateError(error_msg)

    return PixlError(
        error_type=error_type or "unknown",
        message=error_msg,
        is_transient=failure_kind == "transient",
    )


def extract_diff_from_output(text: str) -> str:
    """Extract a unified diff block from LLM output text."""
    match = re.search(r"```diff\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(---\s+.*?\n\+\+\+\s+.*?\n.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = text.split("\n")
    diff_lines = [
        ln for ln in lines if ln.startswith("+") or ln.startswith("-") or ln.startswith("@@")
    ]
    if len(diff_lines) >= 3:
        return "\n".join(diff_lines)
    return ""


def extract_affected_files_from_diff(diff: str) -> list[str]:
    """Extract file paths from diff headers."""
    files = set()
    for match in re.finditer(r"^(?:---|\+\+\+)\s+([ab]/)?(.+)$", diff, re.MULTILINE):
        path = match.group(2).strip()
        if path and path != "/dev/null":
            files.add(path)
    return sorted(files)
