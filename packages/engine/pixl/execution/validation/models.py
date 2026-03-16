"""Data models for contract validation results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContractViolation:
    """A single contract violation."""

    rule: str
    message: str


@dataclass
class ContractValidationResult:
    """Aggregated result of contract validation."""

    violations: list[ContractViolation] = field(default_factory=list)
    git_unavailable_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def violation_messages(self) -> list[str]:
        return [f"[{v.rule}] {v.message}" for v in self.violations]

    @property
    def warning_messages(self) -> list[str]:
        return list(self.warnings)
