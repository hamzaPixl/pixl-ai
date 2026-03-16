"""Typed execution errors for deterministic recovery handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PixlError(Exception):
    """Base error for Pixl execution and recovery."""

    error_type: str
    message: str
    cause: Exception | None = None
    is_transient: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "cause": str(self.cause) if self.cause else None,
            "is_transient": self.is_transient,
            "metadata": self.metadata,
        }


class ProviderError(PixlError):
    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        http_status: int | None = None,
        provider: str | None = None,
        model: str | None = None,
        retry_after: float | None = None,
        is_transient: bool = True,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        meta = metadata or {}
        meta.update(
            {
                "code": code,
                "http_status": http_status,
                "provider": provider,
                "model": model,
                "retry_after": retry_after,
            }
        )
        super().__init__(
            "provider_error",
            message,
            cause=cause,
            is_transient=is_transient,
            metadata=meta,
        )


class TimeoutError(PixlError):
    def __init__(
        self,
        message: str,
        *,
        timeout_s: float | None = None,
        provider: str | None = None,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        meta = metadata or {}
        meta.update({"timeout_s": timeout_s, "provider": provider, "model": model})
        super().__init__(
            "timeout_error",
            message,
            cause=cause,
            is_transient=True,
            metadata=meta,
        )


class ContractError(PixlError):
    def __init__(
        self,
        message: str,
        *,
        rule: str | None = None,
        details: str | None = None,
        artifact_path: str | None = None,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        meta = metadata or {}
        meta.update({"rule": rule, "details": details, "artifact_path": artifact_path})
        super().__init__("contract_error", message, cause=cause, metadata=meta)


class StateError(PixlError):
    def __init__(
        self,
        message: str,
        *,
        invariant: str | None = None,
        details: str | None = None,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        meta = metadata or {}
        meta.update({"invariant": invariant, "details": details})
        super().__init__("state_error", message, cause=cause, metadata=meta)


class StorageError(PixlError):
    def __init__(
        self,
        message: str,
        *,
        op: str | None = None,
        details: str | None = None,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        meta = metadata or {}
        meta.update({"op": op, "details": details})
        super().__init__(
            "storage_error",
            message,
            cause=cause,
            is_transient=False,
            metadata=meta,
        )


class UserActionRequired(PixlError):  # noqa: N818
    def __init__(
        self,
        message: str,
        *,
        kind: str = "gate",
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        meta = metadata or {}
        meta.update({"kind": kind})
        super().__init__(
            "user_action_required",
            message,
            cause=cause,
            is_transient=False,
            metadata=meta,
        )


__all__ = [
    "PixlError",
    "ProviderError",
    "TimeoutError",
    "ContractError",
    "StateError",
    "StorageError",
    "UserActionRequired",
]
