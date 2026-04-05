"""Constants for contract validation.

Centralizes stub detection patterns and contract rule names
used by the ContractValidator.
"""

from __future__ import annotations

# Regex patterns that indicate stub/placeholder code (GAP-09: Distrust Model).
# Each pattern is matched per-line with re.IGNORECASE.
STUB_PATTERNS: list[str] = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bHACK\b",
    r"\bXXX\b",
    r"\bpass\s*$",  # Python bare pass
    r"raise\s+NotImplementedError",
    r"return\s+None\s*$",
    r'return\s+["\']placeholder["\']',
    r"\.\.\.(?:\s*#.*)?$",  # Python ellipsis
    r"// ?not implemented",
    r"# ?not implemented",
    r"throw\s+new\s+Error\(['\"]not implemented",
    r"console\.log\(['\"]TODO",
]

# Regex patterns that indicate hack/shortcut code (integrity protocol).
# Each pattern is matched per-line with re.IGNORECASE.
HACK_PATTERNS: list[str] = [
    r"!important",  # CSS specificity hack
    r"catch\s*\([^)]*\)\s*\{\s*\}",  # empty catch block
    r"catch\s*\{?\s*\}",  # Swift/Kotlin empty catch
    r"except\s*:\s*pass",  # Python bare except pass
    r"eslint-disable(?!-next-line)",  # broad ESLint disable (not targeted next-line)
    r"@ts-ignore",  # TypeScript type suppression
    r"# type:\s*ignore(?!\[)",  # Python type ignore without specific code
    r"noinspection",  # JetBrains suppression
    r"noqa(?!:)",  # Python noqa without specific code
    r'if\s*\(\s*["\'][0-9a-f-]{8,}["\']\s*[=!]==?\s*',  # hardcoded UUID comparison
    r"\.skip\(",  # skipped test
    r"\.only\(",  # focused test left in
]

# Contract rule names for skill/agent enforcement.
RULE_REQUIRED_SKILLS = "required_skills"
RULE_REQUIRED_AGENTS = "required_agents"
