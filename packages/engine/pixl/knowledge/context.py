"""Build context for prompts from knowledge chunks via SQLite FTS."""

from pathlib import Path

from pixl.storage import create_storage


class ContextBuilder:
    """Build context strings for prompt injection."""

    def __init__(self, project_path: Path) -> None:
        self.db = create_storage(project_path)
        self.store = self.db.knowledge

    def build_context(
        self,
        query: str,
        max_tokens: int = 4000,
        include_source: bool = True,
    ) -> str:
        """
        Build context string from relevant chunks.

        Args:
            query: What to search for
            max_tokens: Maximum tokens (estimated)
            include_source: Include source file references

        Returns:
            Formatted context string
        """
        context = self.store.search_for_context(query, max_tokens=max_tokens)
        if not context:
            return ""
        if include_source:
            return context

        lines = [line for line in context.splitlines() if not line.strip().startswith("_Source:")]
        return "\n".join(lines).strip()

    def build_context_for_feature(
        self,
        title: str,
        description: str = "",
        max_tokens: int = 3000,
    ) -> str:
        """
        Build context specifically for a feature.

        Searches using feature title and description.
        """
        return self.store.search_for_feature(
            title=title,
            description=description,
            max_tokens=max_tokens,
        )
