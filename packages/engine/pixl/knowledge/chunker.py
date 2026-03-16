"""Split documents into searchable chunks."""

import re
from dataclasses import dataclass
from pathlib import Path

from pixl.models.knowledge import Chunk, ChunkType

@dataclass
class ChunkConfig:
    """Chunking configuration."""

    max_chunk_size: int = 2000  # Max characters per chunk
    min_chunk_size: int = 50  # Min characters (skip smaller)
    include_code_files: bool = True  # Also index source code
    code_extensions: tuple = (".py", ".ts", ".js", ".go", ".rs")

class Chunker:
    """Split documents into chunks."""

    def __init__(self, config: ChunkConfig | None = None) -> None:
        self.config = config or ChunkConfig()

    def chunk_markdown(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Chunk a markdown file by headers."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(base_path))
        chunks = []

        # Keep the header with its content
        pattern = r"^(#{1,3}\s+.+)$"
        parts = re.split(pattern, content, flags=re.MULTILINE)

        current_title = file_path.stem
        current_content: list[str] = []
        line_num = 1

        for part in parts:
            if re.match(r"^#{1,3}\s+", part):
                if current_content:
                    text = "\n".join(current_content).strip()
                    if len(text) >= self.config.min_chunk_size:
                        chunks.append(
                            self._make_chunk(
                                title=current_title,
                                content=text[: self.config.max_chunk_size],
                                source=rel_path,
                                chunk_type=self._detect_type(text),
                                line_start=line_num,
                            )
                        )
                current_title = part.lstrip("#").strip()
                current_content = []
                line_num += content[: content.find(part)].count("\n") + 1
            else:
                current_content.append(part)

        # Don't forget last chunk
        if current_content:
            text = "\n".join(current_content).strip()
            if len(text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=current_title,
                        content=text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=self._detect_type(text),
                        line_start=line_num,
                    )
                )

        return chunks

    def chunk_code(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Chunk a code file by functions/classes."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(base_path))
        chunks = []

        # Simple heuristic: chunk by function/class definitions
        if file_path.suffix == ".py":
            pattern = r"^((?:async\s+)?(?:def|class)\s+\w+)"
        elif file_path.suffix in (".ts", ".js"):
            pattern = r"^(?:export\s+)?(?:async\s+)?(?:function|class|const\s+\w+\s*=)"
        else:
            # Generic: chunk by blank line separated blocks
            pattern = r"\n\n+"

        parts = re.split(pattern, content, flags=re.MULTILINE)

        for i, part in enumerate(parts):
            if len(part.strip()) >= self.config.min_chunk_size:
                title_match = re.search(r"(?:def|class|function)\s+(\w+)", part)
                title = title_match.group(1) if title_match else f"{file_path.stem}:{i}"

                chunks.append(
                    self._make_chunk(
                        title=title,
                        content=part[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.CODE,
                    )
                )

        return chunks

    def _make_chunk(
        self,
        title: str,
        content: str,
        source: str,
        chunk_type: ChunkType,
        line_start: int | None = None,
    ) -> Chunk:
        """Create a chunk with extracted keywords."""
        return Chunk(
            id=f"{source}:{title}".replace("/", "-").replace(" ", "_").lower(),
            title=title,
            content=content,
            source=source,
            chunk_type=chunk_type,
            keywords=self._extract_keywords(title + " " + content),
            line_start=line_start,
        )

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        # Tokenize
        words = re.findall(r"\b[a-z][a-z0-9_]{2,}\b", text.lower())

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
            "been",
            "being",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "how",
            "what",
            "when",
            "where",
            "why",
            "who",
            "which",
            "their",
            "there",
            "then",
            "than",
            "these",
            "those",
            "some",
            "such",
            "only",
            "other",
            "into",
            "over",
            "after",
            "before",
            "between",
            "under",
            "above",
            "below",
            "also",
            "just",
            "about",
            "like",
            "self",
            "none",
            "true",
            "false",
            "return",
            "import",
        }

        filtered = [w for w in words if w not in stopwords]

        # Count frequency and take top keywords
        freq: dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1

        sorted_words = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)
        return sorted_words[:20]  # Top 20 keywords

    def _detect_type(self, content: str) -> ChunkType:
        """Detect chunk type from content."""
        content_lower = content.lower()

        # Procedure indicators
        if any(
            p in content_lower
            for p in ["step 1", "first,", "then,", "finally,", "how to", "```bash", "```shell"]
        ):
            return ChunkType.PROCEDURE

        # Reference indicators (tables, lists of configs)
        if content.count("|") > 5 or content.count("`") > 10:
            return ChunkType.REFERENCE

        # Code indicators
        if content.count("```") >= 2:
            return ChunkType.CODE

        return ChunkType.CONCEPT
