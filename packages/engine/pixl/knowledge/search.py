"""SQLite FTS-backed search with optional type boosts and cross-references."""

import re
from pathlib import Path

from pixl.models.knowledge import Chunk, ChunkType, SearchResult
from pixl.storage import create_storage

# Query intent detection — determines which chunk types to boost

# Keywords that signal a code-oriented query
_CODE_SIGNALS = frozenset(
    {
        "function",
        "class",
        "method",
        "import",
        "def",
        "const",
        "var",
        "async",
        "await",
        "return",
        "type",
        "interface",
        "implement",
        "parameter",
        "argument",
        "call",
        "invoke",
        "constructor",
        "module",
        "package",
        "library",
        "dependency",
        "endpoint",
    }
)

# Keywords that signal an architecture / concept query
_CONCEPT_SIGNALS = frozenset(
    {
        "architecture",
        "design",
        "pattern",
        "overview",
        "structure",
        "system",
        "component",
        "layer",
        "principle",
        "approach",
        "strategy",
        "concept",
        "philosophy",
        "decision",
        "tradeoff",
    }
)

# Keywords that signal a reference / config query
_REFERENCE_SIGNALS = frozenset(
    {
        "config",
        "configuration",
        "setting",
        "option",
        "flag",
        "environment",
        "variable",
        "schema",
        "table",
        "column",
        "workflow",
        "yaml",
        "yml",
        "json",
        "api",
        "reference",
    }
)

# Keywords that signal a procedural / how-to query
_PROCEDURE_SIGNALS = frozenset(
    {
        "how",
        "step",
        "guide",
        "tutorial",
        "setup",
        "install",
        "deploy",
        "migrate",
        "run",
        "build",
        "test",
        "debug",
        "troubleshoot",
        "fix",
        "resolve",
        "configure",
    }
)

def detect_query_intent(terms: list[str]) -> dict[ChunkType, float]:
    """Detect which chunk types are most relevant for a query.

    Returns a dict mapping ChunkType → boost multiplier (1.0 = neutral).
    """
    term_set = frozenset(terms)

    code_hits = len(term_set & _CODE_SIGNALS)
    concept_hits = len(term_set & _CONCEPT_SIGNALS)
    reference_hits = len(term_set & _REFERENCE_SIGNALS)
    procedure_hits = len(term_set & _PROCEDURE_SIGNALS)

    total = code_hits + concept_hits + reference_hits + procedure_hits
    if total == 0:
        # No signal — neutral weighting
        return dict.fromkeys(ChunkType, 1.0)

    # Boost the dominant type, slightly penalize others
    boosts: dict[ChunkType, float] = {}
    for chunk_type, hits in [
        (ChunkType.CODE, code_hits),
        (ChunkType.CONCEPT, concept_hits),
        (ChunkType.REFERENCE, reference_hits),
        (ChunkType.PROCEDURE, procedure_hits),
    ]:
        if hits > 0:
            boosts[chunk_type] = 1.0 + (hits / total) * 1.5  # up to 2.5×
        else:
            boosts[chunk_type] = 0.8  # slight penalty for non-matching types

    return boosts

# Language extension mapping for scope filtering

_LANG_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "javascript": {".js", ".jsx", ".mjs"},
    "typescript": {".ts", ".tsx"},
    "markdown": {".md", ".mdx"},
    "yaml": {".yaml", ".yml"},
}

def _source_matches_scope(source: str, scope: str) -> bool:
    """Check if a chunk source matches a scope filter.

    Scope can be:
    - A language name: "python", "typescript"
    - A file path substring: "src/auth", "models/"
    - A glob-like suffix: "*.py"
    """
    # Language name
    exts = _LANG_EXTENSIONS.get(scope.lower())
    if exts:
        return any(source.endswith(ext) for ext in exts)

    # Glob suffix
    if scope.startswith("*."):
        return source.endswith(scope[1:])

    # Path substring
    return scope in source

# Cross-reference index

class CrossReferenceIndex:
    """Index of related chunks from the same source file.

    When a search finds a class chunk, this can pull in its method chunks.
    When it finds a section, it can pull in sibling sections.
    """

    def __init__(self, chunks: list[Chunk]) -> None:
        # Group chunks by source file
        self._by_source: dict[str, list[Chunk]] = {}
        for chunk in chunks:
            self._by_source.setdefault(chunk.source, []).append(chunk)

    def get_related(self, chunk: Chunk, limit: int = 3) -> list[Chunk]:
        """Get chunks from the same source file, excluding the chunk itself."""
        siblings = self._by_source.get(chunk.source, [])
        return [s for s in siblings if s.id != chunk.id][:limit]

    def get_siblings_by_title_prefix(self, chunk: Chunk) -> list[Chunk]:
        """Get chunks whose title shares a prefix with this chunk.

        For example, if chunk title is "Calculator", find "Calculator.add",
        "Calculator.subtract". Or if title is "Auth > Login", find "Auth > Signup".
        """
        prefix = chunk.title.split(".")[0].split(" > ")[0].strip()
        if not prefix or len(prefix) < 3:
            return []

        siblings = self._by_source.get(chunk.source, [])
        return [s for s in siblings if s.id != chunk.id and s.title.startswith(prefix)]

# Main search class

class KnowledgeSearch:
    """Search over knowledge chunks with SQLite FTS and type-aware boosts."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.db = create_storage(project_path)
        self.store = self.db.knowledge
        self._chunks: list[Chunk] | None = None
        self._xref: CrossReferenceIndex | None = None

    def reload(self) -> None:
        """Clear cached chunks and cross-reference index.

        Call this after the knowledge index has been rebuilt to pick up new data.
        """
        self._chunks = None
        self._xref = None

    def search(
        self,
        query: str,
        limit: int = 5,
        chunk_types: list[ChunkType] | None = None,
        scope: str | None = None,
        include_related: bool = False,
    ) -> list[SearchResult]:
        """Search chunks by query with enhanced scoring.

        Args:
            query: Search query string
            limit: Maximum results to return
            chunk_types: Filter to specific chunk types only
            scope: Filter by source scope (language name, path, or glob)
            include_related: Include cross-referenced chunks from same source

        Returns:
            List of SearchResult sorted by score
        """
        query = query.strip()
        if not query:
            return []

        query_terms = self._extract_terms(query)
        if not query_terms and not self._uses_fts_syntax(query):
            return []

        query_for_fts = query if self._uses_fts_syntax(query) else " ".join(query_terms)
        phrase = query.lower() if len(query_terms) > 1 else ""

        # Detect query intent for type-aware boosting
        type_boosts = (
            detect_query_intent(query_terms) if query_terms else dict.fromkeys(ChunkType, 1.0)
        )

        type_values = None
        if chunk_types:
            type_values = [t.value if isinstance(t, ChunkType) else str(t) for t in chunk_types]

        source_filter = None
        if scope and not _LANG_EXTENSIONS.get(scope.lower()) and not scope.startswith("*."):
            source_filter = scope

        raw_limit = max(limit * 5, limit)
        rows = self.store.search(
            query=query_for_fts,
            limit=raw_limit,
            chunk_types=type_values,
            source_filter=source_filter,
        )

        results: list[SearchResult] = []
        for row in rows:
            chunk = self._row_to_chunk(row)
            if scope and not _source_matches_scope(chunk.source, scope):
                continue
            score, matched = self._score_result(
                chunk, row["score"], query_terms, type_boosts, phrase
            )
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                    matched_terms=matched,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        top_results = results[:limit]

        if phrase:

            def _has_phrase(res: SearchResult) -> bool:
                text = f"{res.chunk.title} {res.chunk.content}".lower()
                return phrase in text

            if not any(_has_phrase(r) for r in top_results):
                phrase_matches = [r for r in results if _has_phrase(r)]
                if phrase_matches:
                    best_phrase = phrase_matches[0]
                    top_results = [best_phrase] + [
                        r for r in top_results if r.chunk.id != best_phrase.chunk.id
                    ]
                    top_results = top_results[:limit]

        results = top_results

        # Optionally include cross-referenced chunks
        if include_related and results:
            results = self._expand_with_related(results, limit)

        return results

    def _get_chunks(self) -> list[Chunk]:
        """Load chunks (cached)."""
        if self._chunks is None:
            rows = self.store.list_chunks()
            self._chunks = [self._row_to_chunk(row) for row in rows]
            self._xref = None  # invalidate cross-reference index
        return self._chunks

    def _get_xref(self) -> CrossReferenceIndex:
        """Get cross-reference index (cached)."""
        if self._xref is None:
            self._xref = CrossReferenceIndex(self._get_chunks())
        return self._xref

    def _extract_terms(self, query: str) -> list[str]:
        """Extract search terms from query."""
        words = re.findall(r"\b[a-z][a-z0-9_]{2,}\b", query.lower())
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "have",
            "are",
            "was",
            "will",
            "can",
            "how",
            "what",
            "when",
            "where",
            "why",
            "who",
        }
        return [w for w in words if w not in stopwords]

    def _uses_fts_syntax(self, query: str) -> bool:
        """Detect whether query uses explicit FTS syntax."""
        return '"' in query or " AND " in query or " OR " in query or " NOT " in query

    def _row_to_chunk(self, row: dict[str, object]) -> Chunk:
        """Convert a SQLite row dict into a Chunk model."""
        chunk_type = row.get("chunk_type", "concept")
        try:
            parsed_type = ChunkType(str(chunk_type))
        except ValueError:
            parsed_type = ChunkType.CONCEPT

        keywords = row.get("keywords") or []
        if isinstance(keywords, str):
            keywords = keywords.split()

        return Chunk(
            id=str(row.get("id", "")),
            title=str(row.get("title", "")),
            content=str(row.get("content", "")),
            source=str(row.get("source", "")),
            chunk_type=parsed_type,
            keywords=list(keywords),
            line_start=row.get("line_start"),
            line_end=row.get("line_end"),
        )

    def _score_result(
        self,
        chunk: Chunk,
        bm25_score: float,
        terms: list[str],
        type_boosts: dict[ChunkType, float],
        phrase: str = "",
    ) -> tuple[float, list[str]]:
        """Score a chunk using inverted BM25 plus type boost."""
        base_score = 1.0 / (bm25_score + 1.0)
        boost = type_boosts.get(chunk.chunk_type, 1.0)
        score = base_score * boost

        if not terms:
            return score, []

        text = f"{chunk.title} {chunk.content} {' '.join(chunk.keywords)}".lower()
        if phrase and phrase in text:
            score *= 1.5
        matched = sorted({term for term in terms if term in text})
        return score, matched

    def _expand_with_related(self, results: list[SearchResult], limit: int) -> list[SearchResult]:
        """Expand results with cross-referenced related chunks."""
        xref = self._get_xref()
        seen_ids = {r.chunk.id for r in results}
        expanded = list(results)

        for result in results:
            if len(expanded) >= limit * 2:
                break

            def _append_related(chunks: list[Chunk], _result: SearchResult = result) -> None:
                for chunk in chunks:
                    if len(expanded) >= limit * 2:
                        break
                    if chunk.id in seen_ids:
                        continue
                    # Related chunks get a fraction of the parent score
                    expanded.append(
                        SearchResult(
                            chunk=chunk,
                            score=_result.score * 0.5,
                            matched_terms=_result.matched_terms,
                        )
                    )
                    seen_ids.add(chunk.id)

            # Title-prefix siblings first (stronger relevance)
            _append_related(xref.get_siblings_by_title_prefix(result.chunk))

            # Then include same-source siblings to broaden context
            if len(expanded) < limit * 2:
                _append_related(
                    xref.get_related(
                        result.chunk,
                        limit=(limit * 2) - len(expanded),
                    )
                )

        return expanded
