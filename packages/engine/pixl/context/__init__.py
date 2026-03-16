"""Context optimization module for token-efficient workflow execution.

This module implements the unified context system that provides:
- Baton context rendering (goal, state, decisions, constraints)
- Budget-aware artifact selection (summary > diff > excerpt > full)
- Predecessor outputs from structured mode
- Unified envelope instructions with baton_patch in payload

Key components:
- UnifiedContextCompiler: Assembles per-model prompts with baton context
- ArtifactSummarizer: Generates and caches LLM summaries of artifacts
- ArtifactDiffer: Generates diffs between artifact versions
"""

from pixl.context.differ import ArtifactDiffer
from pixl.context.summarizer import ArtifactSummarizer
from pixl.context.unified_compiler import UnifiedContextCompiler

__all__ = [
    "UnifiedContextCompiler",
    "ArtifactSummarizer",
    "ArtifactDiffer",
]
