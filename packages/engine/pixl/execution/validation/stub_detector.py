"""Stub/placeholder detection for contract validation (GAP-09: Distrust Model)."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from pixl.execution.contract_constants import STUB_PATTERNS
from pixl.execution.validation.models import ContractValidationResult, ContractViolation


def detect_stubs(
    files: list[str],
    resolve_path: Callable[[str], Path],
    result: ContractValidationResult,
    stub_patterns: list[str] | None = None,
) -> list[dict[str, str]]:
    """Scan files for stub/placeholder patterns indicating incomplete implementation.

    Args:
        files: List of file paths to scan
        resolve_path: Callable to resolve a relative path to an absolute Path
        result: ContractValidationResult to accumulate violations
        stub_patterns: Optional override for stub patterns (defaults to STUB_PATTERNS)

    Returns:
        List of detected stubs with file, line number, and matched pattern
    """
    patterns = stub_patterns if stub_patterns is not None else STUB_PATTERNS
    stubs: list[dict[str, str]] = []

    for path in files:
        resolved = resolve_path(path)
        if not resolved.exists():
            continue

        try:
            content = resolved.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    stubs.append(
                        {
                            "file": path,
                            "line": str(line_num),
                            "content": line.strip()[:120],
                            "pattern": pattern,
                        }
                    )
                    break  # One match per line is enough

    if stubs:
        result.violations.append(
            ContractViolation(
                rule="stub_detected",
                message=(
                    f"Found {len(stubs)} stub/placeholder pattern(s) in implementation: "
                    + "; ".join(f"{s['file']}:{s['line']}" for s in stubs[:5])
                    + ("..." if len(stubs) > 5 else "")
                ),
            )
        )

    return stubs
