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

# Contract rule names for skill/agent enforcement.
RULE_REQUIRED_SKILLS = "required_skills"
RULE_REQUIRED_AGENTS = "required_agents"
