"""Context slice models for the context compiler.

These models represent the three-layer artifact representation and
the compiled context output used by the context compiler to assemble
minimal, auditable prompts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from pixl.models.baton import ArtifactRef, Baton


class ArtifactLayer(BaseModel):
    """Three-layer artifact representation.

    For any artifact, the context compiler selects the cheapest layer
    that provides sufficient context:
    1. summary (10-30 lines, LLM-generated, cached)
    2. diff (last change since previous version)
    3. excerpt (selected line range)
    4. full (entire content - only when explicitly needed)
    """

    ref: ArtifactRef = Field(description="Artifact reference (id, hash, type)")
    summary: str | None = Field(
        default=None,
        description="10-30 line summary, LLM-generated and cached by hash",
    )
    diff: str | None = Field(
        default=None,
        description="Unified diff of last change since previous version",
    )
    excerpt: str | None = Field(
        default=None,
        description="Selected line range from the artifact",
    )
    full_content: str | None = Field(
        default=None,
        description="Full artifact content (only included when necessary)",
    )

    def best_available_layer(self) -> str:
        """Return the name of the cheapest available layer.

        Returns:
            Layer name: 'summary', 'diff', 'excerpt', or 'full'.
        """
        if self.summary is not None:
            return "summary"
        if self.diff is not None:
            return "diff"
        if self.excerpt is not None:
            return "excerpt"
        if self.full_content is not None:
            return "full"
        return "summary"  # Indicates summary should be generated

    def get_content_for_layer(self, layer: str) -> str | None:
        """Get content for a specific layer.

        Args:
            layer: One of 'summary', 'diff', 'excerpt', 'full'.

        Returns:
            Content string or None if layer not available.
        """
        return {
            "summary": self.summary,
            "diff": self.diff,
            "excerpt": self.excerpt,
            "full": self.full_content,
        }.get(layer)

    def estimate_tokens(self, layer: str | None = None) -> int:
        """Estimate token count for a layer.

        Args:
            layer: Specific layer, or None for best available.

        Returns:
            Estimated token count.
        """
        from pixl.utils.tokens import estimate_tokens as _estimate

        if layer is None:
            layer = self.best_available_layer()
        content = self.get_content_for_layer(layer)
        if content is None:
            return 0
        return _estimate(content, "default")


class ContextSlice(BaseModel):
    """A single included source with audit trail.

    Each slice records what was included in the compiled prompt and why,
    enabling full auditability and reproducibility.
    """

    artifact_id: str = Field(description="Artifact ID (art-XXXX)")
    hash: str = Field(description="SHA256 hash of the artifact at inclusion time")
    layer: Literal["summary", "diff", "excerpt", "full"] = Field(
        description="Which layer of the artifact was included",
    )
    excerpt_range: tuple[int, int] | None = Field(
        default=None,
        description="Line range (start, end) if layer is 'excerpt'",
    )
    reason: str = Field(
        description="Why this slice was included (e.g., 'required_artifact', 'frozen', 'work_scope')",
    )
    token_estimate: int = Field(
        description="Estimated token count of this slice",
    )
    content: str = Field(
        default="",
        description="The actual content included in the prompt",
    )

    def to_audit_entry(self) -> dict[str, Any]:
        """Convert to audit log entry.

        Returns:
            Dictionary suitable for session.context_audit.
        """
        entry = {
            "artifact_id": self.artifact_id,
            "hash": self.hash,
            "layer": self.layer,
            "reason": self.reason,
            "token_estimate": self.token_estimate,
        }
        if self.excerpt_range:
            entry["excerpt_range"] = list(self.excerpt_range)
        return entry


class CompiledContext(BaseModel):
    """Output of the context compiler.

    Contains the assembled prompt text plus full audit trail of what
    was included and why. The prompt_text is what gets sent to the LLM.
    """

    baton: Baton = Field(description="Current baton state")
    stage_contract_summary: str = Field(
        default="",
        description="Summary of what this stage must produce",
    )
    slices: list[ContextSlice] = Field(
        default_factory=list,
        description="All included context slices with audit trail",
    )
    total_tokens: int = Field(
        default=0,
        description="Total estimated token count of the compiled prompt",
    )
    budget_tokens: int = Field(
        default=0,
        description="Token budget for this model tier",
    )
    prompt_text: str = Field(
        default="",
        description="Final assembled prompt text sent to the LLM",
    )

    @property
    def budget_utilization(self) -> float:
        """Percentage of budget used.

        Returns:
            Utilization as a float between 0.0 and 1.0+.
        """
        if self.budget_tokens <= 0:
            return 0.0
        return self.total_tokens / self.budget_tokens

    @property
    def slice_count(self) -> int:
        """Number of context slices included."""
        return len(self.slices)

    def to_audit_log(self) -> dict[str, Any]:
        """Convert to audit log entry for session.context_audit.

        Returns:
            Dictionary with compilation metadata and slice details.
        """
        return {
            "total_tokens": self.total_tokens,
            "budget_tokens": self.budget_tokens,
            "utilization": round(self.budget_utilization, 3),
            "slice_count": self.slice_count,
            "slices": [s.to_audit_entry() for s in self.slices],
        }

    def to_full_audit_log(self) -> dict[str, Any]:
        """Convert to full audit log entry including the assembled prompt text.

        Returns:
            Dictionary with compilation metadata, slice details, and prompt text.
        """
        entry = self.to_audit_log()
        entry["prompt_text"] = self.prompt_text
        return entry


__all__ = [
    "ArtifactLayer",
    "ContextSlice",
    "CompiledContext",
]
