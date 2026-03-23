"""Goal-backward verification for contract validation (GAP-02)."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from pixl.execution.validation.models import ContractValidationResult, ContractViolation


def verify_success_criteria(
    success_criteria: list[str],
    changed_files: list[str],
    resolve_path: Callable[[str], Path],
    result: ContractValidationResult,
) -> dict[str, bool]:
    """Verify implementation against explicit success criteria.

    Uses file content scanning to check whether success criteria
    have corresponding implementation evidence. This is a heuristic
    check -- not a substitute for test execution.

    Args:
        success_criteria: List of criteria strings from the feature/plan
        changed_files: List of files modified during implementation
        resolve_path: Callable to resolve a relative path to an absolute Path
        result: ContractValidationResult to accumulate violations

    Returns:
        Dict mapping each criterion to whether evidence was found
    """
    criteria_status: dict[str, bool] = {}

    for criterion in success_criteria:
        key_terms = extract_key_terms(criterion)
        evidence_found = False

        for path in changed_files:
            resolved = resolve_path(path)
            if not resolved.exists():
                continue

            try:
                content = resolved.read_text(encoding="utf-8").lower()
            except (UnicodeDecodeError, OSError):
                continue

            matches = sum(1 for term in key_terms if term.lower() in content)
            if matches >= max(1, len(key_terms) // 2):
                evidence_found = True
                break

        criteria_status[criterion] = evidence_found

        if not evidence_found:
            result.violations.append(
                ContractViolation(
                    rule="success_criteria_unmet",
                    message=f"No implementation evidence for: {criterion[:100]}",
                )
            )

    return criteria_status


def extract_key_terms(text: str) -> list[str]:
    """Extract meaningful terms from a criterion for evidence search.

    Filters out common stop words and returns unique terms of 3+ chars.
    """
    stop_words = {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "had",
        "her",
        "was",
        "one",
        "our",
        "out",
        "has",
        "have",
        "been",
        "should",
        "must",
        "will",
        "shall",
        "that",
        "this",
        "with",
        "from",
        "they",
        "said",
        "each",
        "which",
        "their",
        "when",
        "into",
    }
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", text)
    return [w for w in words if len(w) >= 3 and w.lower() not in stop_words]
