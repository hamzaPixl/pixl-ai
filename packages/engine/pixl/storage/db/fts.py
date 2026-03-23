"""Shared FTS5 query preparation utility.

Normalizes user search queries into valid SQLite FTS5 MATCH syntax.
Used by ArtifactDB, IncidentDB, and KnowledgeDB.
"""

from __future__ import annotations


def prepare_fts_query(query: str) -> str:
    """Prepare a user query for FTS5 MATCH syntax.

    Handles:
    - Empty/whitespace queries → empty string (caller should skip MATCH)
    - FTS5 operator syntax (quotes, AND, OR, NOT) → passed through
    - Simple words → cleaned, filtered (min 2 chars), joined with OR

    Returns:
        FTS5-safe query string, or empty string if no valid terms.
    """
    if not query or not query.strip():
        return ""

    # If the query already uses FTS5 syntax, pass through
    if '"' in query or " AND " in query or " OR " in query or " NOT " in query:
        return query

    words = []
    for word in query.split():
        cleaned = "".join(c for c in word if c.isalnum() or c in "_-")
        if len(cleaned) >= 2:
            words.append(cleaned)

    return " OR ".join(words) if words else ""
