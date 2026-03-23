"""Pure-function recovery policy for typed PixlError subtypes.

Maps each error type to a deterministic RecoveryDecision with no side effects.
Can optionally use incident history to bias decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pixl.errors import (
    ContractError,
    PixlError,
    ProviderError,
    StateError,
    StorageError,
    TimeoutError,
    UserActionRequired,
)

if TYPE_CHECKING:
    from pixl.recovery.incident_store import IncidentStore


class RecoveryAction(StrEnum):
    """Actions the recovery engine can prescribe."""

    RETRY = "retry"
    FAIL_FAST = "fail_fast"
    FAILOVER = "failover"
    CONTRACT_REPAIR = "contract_repair"
    PATCH_AND_TEST = "patch_and_test"
    REQUIRE_HUMAN = "require_human"


@dataclass(frozen=True)
class RecoveryDecision:
    """Immutable decision returned by the recovery policy."""

    action: RecoveryAction
    reason: str
    max_attempts: int
    current_attempt: int
    backoff_seconds: float = 0.0
    jitter_range: float = 0.0
    should_execute: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def _exponential_backoff(
    attempt: int,
    base: float,
    max_seconds: float,
) -> float:
    """Compute deterministic exponential backoff: base * 2^attempt, capped.

    Args:
        attempt: Current attempt number (0-based).
        base: Base delay in seconds.
        max_seconds: Maximum delay cap.

    Returns:
        Backoff duration in seconds (deterministic).
    """
    return min(base * (2**attempt), max_seconds)


def decide_recovery(
    error: PixlError,
    attempt: int,
    incident_store: IncidentStore | None = None,
    max_attempts_override: int | None = None,
) -> RecoveryDecision:
    """Determine recovery action for a given error and attempt count.

    Pure function — no I/O, no side effects. If incident_store is provided,
    queries similar incidents and biases the decision based on history.

    Incident history is only considered for error types that allow
    retry (ProviderError, TimeoutError, ContractError). Deterministic
    errors (StateError, UserActionRequired, StorageError) always return
    their fixed action regardless of history.

    Args:
        error: The typed PixlError that occurred.
        attempt: Current attempt number (0-based).
        incident_store: Optional IncidentStore for history-based biasing.
        max_attempts_override: Optional global max-attempts override.

    Returns:
        A frozen RecoveryDecision prescribing the action.
    """
    # Deterministic errors are not influenced by incident history
    if isinstance(error, StateError):
        return RecoveryDecision(
            action=RecoveryAction.FAIL_FAST,
            reason="State errors cannot be auto-corrected",
            max_attempts=0,
            current_attempt=attempt,
        )

    if isinstance(error, UserActionRequired):
        return RecoveryDecision(
            action=RecoveryAction.REQUIRE_HUMAN,
            reason="Human action required",
            max_attempts=0,
            current_attempt=attempt,
        )

    if isinstance(error, StorageError):
        return RecoveryDecision(
            action=RecoveryAction.FAIL_FAST,
            reason="Storage errors cannot be retried (persistence unavailable)",
            max_attempts=0,
            current_attempt=attempt,
        )

    # Check incident history for retry-eligible errors
    if incident_store and max_attempts_override is None:
        biased_decision = _apply_incident_bias(error, attempt, incident_store)
        if biased_decision is not None:
            return biased_decision

    if isinstance(error, ProviderError):
        return _decide_provider_recovery(error, attempt, max_attempts_override)

    if isinstance(error, TimeoutError):
        max_attempts = max_attempts_override if max_attempts_override is not None else 2
        if attempt < max_attempts:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="Timeout, retrying with backoff",
                max_attempts=max_attempts,
                current_attempt=attempt,
                backoff_seconds=_exponential_backoff(attempt, base=2.0, max_seconds=30.0),
                should_execute=True,
            )
        return RecoveryDecision(
            action=RecoveryAction.FAIL_FAST,
            reason="Timeout persisted after retries",
            max_attempts=max_attempts,
            current_attempt=attempt,
        )

    if isinstance(error, ContractError):
        max_attempts = max_attempts_override if max_attempts_override is not None else 2
        if attempt < max_attempts:
            return RecoveryDecision(
                action=RecoveryAction.CONTRACT_REPAIR,
                reason="Contract violation, attempting artifact repair",
                max_attempts=max_attempts,
                current_attempt=attempt,
                should_execute=True,
            )

        # Contract repair exhausted — check if code-level patch makes sense
        rule = error.metadata.get("rule", "")
        code_fixable_rules = {
            "must_update_files",
            "require_regression_test",
            "detect_stubs",
        }
        patch_max_attempts = max_attempts if max_attempts_override is not None else max_attempts + 1
        if rule in code_fixable_rules and attempt < patch_max_attempts:
            return RecoveryDecision(
                action=RecoveryAction.PATCH_AND_TEST,
                reason=f"Contract repair exhausted, attempting patch+test for '{rule}'",
                max_attempts=patch_max_attempts,
                current_attempt=attempt,
                should_execute=True,
                metadata={"contract_rule": rule},
            )

        return RecoveryDecision(
            action=RecoveryAction.FAIL_FAST,
            reason="Contract repair exhausted",
            max_attempts=max_attempts,
            current_attempt=attempt,
        )

    # Unknown/base PixlError — conservative default
    return RecoveryDecision(
        action=RecoveryAction.REQUIRE_HUMAN,
        reason="Unknown error type, human review required",
        max_attempts=0,
        current_attempt=attempt,
    )


def _decide_provider_recovery(
    error: ProviderError,
    attempt: int,
    max_attempts_override: int | None = None,
) -> RecoveryDecision:
    """Provider-specific recovery logic based on HTTP status codes."""
    http_status = error.metadata.get("http_status")
    retry_after = error.metadata.get("retry_after")

    # 429 — rate limit
    if http_status == 429:
        max_attempts = max_attempts_override if max_attempts_override is not None else 5
        if attempt < max_attempts:
            if retry_after is not None:
                backoff = float(retry_after)
            else:
                backoff = _exponential_backoff(attempt, base=1.0, max_seconds=60.0)
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="Rate limited (429), retrying",
                max_attempts=max_attempts,
                current_attempt=attempt,
                backoff_seconds=backoff,
                should_execute=True,
                metadata={"http_status": 429},
            )
        return RecoveryDecision(
            action=RecoveryAction.FAIL_FAST,
            reason="Rate limit retries exhausted",
            max_attempts=max_attempts,
            current_attempt=attempt,
            metadata={"http_status": 429},
        )

    # 4xx (non-429) — client errors, no retry
    if http_status is not None and 400 <= http_status < 500:
        return RecoveryDecision(
            action=RecoveryAction.FAIL_FAST,
            reason=f"Client error ({http_status}), not retryable",
            max_attempts=0,
            current_attempt=attempt,
            metadata={"http_status": http_status},
        )

    # 5xx or no status — server errors, retry with longer backoff + jitter
    max_attempts = max_attempts_override if max_attempts_override is not None else 5
    if attempt < max_attempts:
        backoff = _exponential_backoff(attempt, base=30.0, max_seconds=300.0)
        return RecoveryDecision(
            action=RecoveryAction.RETRY,
            reason="Server error, retrying with backoff",
            max_attempts=max_attempts,
            current_attempt=attempt,
            backoff_seconds=backoff,
            jitter_range=backoff * 0.25,
            should_execute=True,
            metadata={"http_status": http_status},
        )
    return RecoveryDecision(
        action=RecoveryAction.FAIL_FAST,
        reason="Server error retries exhausted",
        max_attempts=max_attempts,
        current_attempt=attempt,
        metadata={"http_status": http_status},
    )


def _apply_incident_bias(
    error: PixlError,
    attempt: int,
    incident_store: IncidentStore,
) -> RecoveryDecision | None:
    """Apply incident history biasing to recovery decisions.

    Uses historical incident outcomes to adjust the default policy:
    - High failure rate (>70%) on similar errors → REQUIRE_HUMAN
    - High success rate with retries → Increase max_attempts
    - Mixed outcomes → Stick with default policy

    Args:
        error: The current error
        attempt: Current attempt number
        incident_store: IncidentStore for querying history

    Returns:
        A biased RecoveryDecision, or None to use default policy
    """
    similar = incident_store.find_similar(error, limit=5)

    if not similar:
        return None

    failed_count = sum(1 for s in similar if s.outcome == "failed")
    escalated_count = sum(1 for s in similar if s.outcome == "escalated")
    succeeded_count = sum(1 for s in similar if s.outcome == "succeeded")

    total = len(similar)
    fail_rate = (failed_count + escalated_count) / total

    # If similar incidents mostly failed, require human intervention
    if fail_rate > 0.7:
        return RecoveryDecision(
            action=RecoveryAction.REQUIRE_HUMAN,
            reason=f"Similar incidents {fail_rate:.0%} failed/escalated",
            max_attempts=0,
            current_attempt=attempt,
            metadata={
                "incident_bias": True,
                "similar_count": total,
                "fail_rate": fail_rate,
            },
        )

    # If similar incidents mostly succeeded, increase retry budget
    success_rate = succeeded_count / total
    if success_rate > 0.7 and attempt < 3:
        succeeded_similar = [s for s in similar if s.outcome == "succeeded"]
        if succeeded_similar:
            # Use the recovery action from the most recent successful incident
            recovery_action = succeeded_similar[0].recovery_action

            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason=f"Similar incidents {success_rate:.0%} succeeded",
                max_attempts=3,  # Increase from default
                current_attempt=attempt,
                backoff_seconds=_exponential_backoff(attempt, base=1.0, max_seconds=60.0),
                should_execute=True,
                metadata={
                    "incident_bias": True,
                    "similar_count": total,
                    "success_rate": success_rate,
                    "suggested_action": recovery_action,
                },
            )

    # Mixed or unclear outcomes — defer to default policy
    return None
