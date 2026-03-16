"""Token estimation utilities.

Provides content-type-aware token estimation without requiring
external tokenizer dependencies.
"""

from __future__ import annotations

from typing import Literal

# Chars-per-token ratios by content type (empirically measured;
# conservative estimates that slightly over-count tokens to stay
# within budgets).
_RATIOS: dict[str, float] = {
    "code": 3.5,
    "json": 3.8,
    "diff": 3.5,
    "markdown": 4.0,
    "prose": 4.2,
    "default": 3.8,
}

ContentType = Literal["code", "json", "diff", "markdown", "prose", "default"]


def estimate_tokens(
    text: str,
    content_type: ContentType = "default",
) -> int:
    """Estimate token count for text using content-type-aware ratios.

    Args:
        text: Text to estimate tokens for.
        content_type: Type of content for ratio selection.

    Returns:
        Estimated token count (0 for empty string, otherwise >= 1).
    """
    if not text:
        return 0
    ratio = _RATIOS.get(content_type, _RATIOS["default"])
    return max(1, int(len(text) / ratio))
