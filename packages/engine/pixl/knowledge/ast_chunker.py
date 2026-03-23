"""Tree-sitter based AST chunker for semantically meaningful chunks.

Replaces the regex-based chunker with tree-sitter parsing to produce
structurally aware chunks from code and documentation files.

Supported languages:
- Python (.py)       — functions, classes, module docstrings
- JavaScript (.js)   — functions, classes, exports
- TypeScript (.ts)   — functions, classes, exports
- Markdown (.md)     — sections by heading hierarchy
- YAML (.yaml/.yml)  — top-level mapping keys

Falls back to the regex chunker for unsupported file types.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pixl.knowledge.chunker import ChunkConfig, Chunker
from pixl.models.knowledge import Chunk, ChunkType

if TYPE_CHECKING:
    from tree_sitter import Node

logger = logging.getLogger(__name__)
_NO_PARSER = object()

# Language registry


@dataclass(frozen=True)
class LanguageSpec:
    """Specification for a supported language grammar."""

    name: str
    extensions: tuple[str, ...]
    loader: str  # dotted import path to the language function


_LANGUAGE_SPECS: dict[str, LanguageSpec] = {
    "python": LanguageSpec("python", (".py",), "tree_sitter_python.language"),
    "javascript": LanguageSpec(
        "javascript", (".js", ".jsx", ".mjs"), "tree_sitter_javascript.language"
    ),
    "typescript": LanguageSpec(
        "typescript", (".ts", ".tsx"), "tree_sitter_typescript.language_typescript"
    ),
    "markdown": LanguageSpec("markdown", (".md", ".mdx"), "tree_sitter_markdown.language"),
    "yaml": LanguageSpec("yaml", (".yaml", ".yml"), "tree_sitter_yaml.language"),
}

# Reverse map: extension → language name
_EXT_TO_LANG: dict[str, str] = {}
for _lang, _spec in _LANGUAGE_SPECS.items():
    for _ext in _spec.extensions:
        _EXT_TO_LANG[_ext] = _lang

# AST Chunker


class ASTChunker(Chunker):
    """Tree-sitter based chunker that extends the regex Chunker.

    Uses tree-sitter grammars for supported languages and falls back
    to the parent regex-based Chunker for unsupported file types.
    """

    def __init__(self, config: ChunkConfig | None = None) -> None:
        super().__init__(config)
        self._parsers: dict[str, object] = {}  # lang_name → Parser
        self._available: bool | None = None  # lazy check

    # Public API (same signature as Chunker)

    def chunk_markdown(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Chunk a Markdown file using tree-sitter section parsing."""
        parser = self._get_parser("markdown")
        if parser is None:
            return self._chunk_markdown_fallback(file_path, base_path)

        source = file_path.read_bytes()
        tree = parser.parse(source)
        rel_path = str(file_path.relative_to(base_path))

        chunks: list[Chunk] = []
        self._walk_markdown_sections(tree.root_node, source, rel_path, chunks)
        return chunks

    def chunk_code(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Chunk a code file using tree-sitter AST."""
        lang = _EXT_TO_LANG.get(file_path.suffix)
        if lang is None or lang == "markdown":
            return super().chunk_code(file_path, base_path)

        parser = self._get_parser(lang)
        if parser is None:
            if lang == "python":
                return self._chunk_python_fallback(file_path, base_path)
            if lang in ("javascript", "typescript"):
                return self._chunk_js_ts_fallback(file_path, base_path)
            if lang == "yaml":
                return self._chunk_yaml_fallback(file_path, base_path)
            return super().chunk_code(file_path, base_path)

        source = file_path.read_bytes()
        tree = parser.parse(source)
        rel_path = str(file_path.relative_to(base_path))

        if lang == "python":
            return self._chunk_python(tree.root_node, source, rel_path)
        elif lang in ("javascript", "typescript"):
            return self._chunk_js_ts(tree.root_node, source, rel_path)
        elif lang == "yaml":
            return self._chunk_yaml(tree.root_node, source, rel_path)
        else:
            return super().chunk_code(file_path, base_path)

    def chunk_yaml(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Chunk a YAML file using tree-sitter AST."""
        parser = self._get_parser("yaml")
        if parser is None:
            return self._chunk_yaml_fallback(file_path, base_path)

        source = file_path.read_bytes()
        tree = parser.parse(source)
        rel_path = str(file_path.relative_to(base_path))
        return self._chunk_yaml(tree.root_node, source, rel_path)

    # Markdown chunking — section-based

    def _walk_markdown_sections(
        self,
        node: Node,
        source: bytes,
        rel_path: str,
        chunks: list[Chunk],
        parent_title: str = "",
    ) -> None:
        """Recursively walk Markdown sections and create chunks.

        tree-sitter-markdown structures:
            document → section → (atx_heading, paragraph, list, section, ...)

        Each ``section`` becomes a chunk. Nested sections are collected
        as child chunks with breadcrumb-style titles (Parent > Child).
        """
        if node.type == "document":
            for child in node.children:
                self._walk_markdown_sections(child, source, rel_path, chunks, parent_title)
            return

        if node.type != "section":
            return

        heading_node = None
        for child in node.children:
            if child.type == "atx_heading":
                heading_node = child
                break

        title = self._extract_heading_text(heading_node, source) if heading_node else ""
        full_title = (
            f"{parent_title} > {title}" if parent_title and title else (title or parent_title)
        )

        body_parts: list[str] = []
        child_sections: list[Node] = []

        for child in node.children:
            if child.type == "section":
                child_sections.append(child)
            elif child.type != "atx_heading":
                text = _node_text(child, source).strip()
                if text:
                    body_parts.append(text)

        body = "\n\n".join(body_parts)

        content_len = len(body) + len(full_title or "")
        if body and content_len >= self.config.min_chunk_size:
            chunk_content = body[: self.config.max_chunk_size]
            chunks.append(
                self._make_chunk(
                    title=full_title or Path(rel_path).stem,
                    content=chunk_content,
                    source=rel_path,
                    chunk_type=self._detect_type(chunk_content),
                    line_start=node.start_point[0] + 1,
                )
            )

        # Recurse into child sections
        for child_section in child_sections:
            self._walk_markdown_sections(child_section, source, rel_path, chunks, full_title)

    def _extract_heading_text(self, heading_node: Node, source: bytes) -> str:
        """Extract clean heading text from an atx_heading node."""
        for child in heading_node.children:
            if child.type == "inline":
                return _node_text(child, source).strip()
        # Fallback: strip leading # markers
        raw = _node_text(heading_node, source).strip()
        return raw.lstrip("#").strip()

    def _chunk_markdown_fallback(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Fallback Markdown chunking with heading breadcrumbs."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(base_path))
        lines = content.splitlines()

        headings: list[tuple[int, int, str]] = []
        for idx, line in enumerate(lines):
            match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                headings.append((idx, level, title))

        if not headings:
            return super().chunk_markdown(file_path, base_path)

        chunks: list[Chunk] = []
        stack: list[tuple[int, str]] = []

        for i, (idx, level, title) in enumerate(headings):
            while stack and stack[-1][0] >= level:
                stack.pop()

            breadcrumb = " > ".join([t for _, t in stack] + [title])
            stack.append((level, title))

            next_idx = headings[i + 1][0] if i + 1 < len(headings) else len(lines)
            body = "\n".join(lines[idx + 1 : next_idx]).strip()

            content_len = len(body) + len(breadcrumb)
            if body and content_len >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=breadcrumb or Path(rel_path).stem,
                        content=body[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=self._detect_type(body),
                        line_start=idx + 1,
                    )
                )

        return chunks

    # Fallback chunking (no tree-sitter)

    def _chunk_python_fallback(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Fallback Python chunking using the built-in ast module."""
        import ast

        source_text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(base_path))
        stem = Path(rel_path).stem
        lines = source_text.splitlines()

        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return self._chunk_python_regex_fallback(source_text, rel_path, stem, lines)

        def _segment(node: ast.AST) -> str:
            try:
                segment = ast.get_source_segment(source_text, node)
            except Exception:
                segment = None
            if segment:
                return segment
            lineno = getattr(node, "lineno", 1)
            end_lineno = getattr(node, "end_lineno", lineno)
            return "\n".join(lines[lineno - 1 : end_lineno])

        chunks: list[Chunk] = []

        # Module docstring
        if tree.body:
            first = tree.body[0]
            if isinstance(first, ast.Expr) and isinstance(
                getattr(first, "value", None), ast.Constant
            ):
                value = first.value.value
                if isinstance(value, str):
                    docstring = value.strip()
                    if len(docstring) >= self.config.min_chunk_size:
                        chunks.append(
                            self._make_chunk(
                                title=f"{stem} (module)",
                                content=docstring[: self.config.max_chunk_size],
                                source=rel_path,
                                chunk_type=ChunkType.CONCEPT,
                                line_start=getattr(first, "lineno", 1),
                            )
                        )

        # Imports
        import_nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        if import_nodes:
            import_text = "\n".join(_segment(n) for n in import_nodes).strip()
            if len(import_text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=f"{stem} (imports)",
                        content=import_text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.REFERENCE,
                        line_start=getattr(import_nodes[0], "lineno", 1),
                    )
                )

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                text = _segment(node)
                if len(text) >= self.config.min_chunk_size:
                    chunks.append(
                        self._make_chunk(
                            title=node.name,
                            content=text[: self.config.max_chunk_size],
                            source=rel_path,
                            chunk_type=ChunkType.CODE,
                            line_start=getattr(node, "lineno", 1),
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                class_text = _segment(node)
                if len(class_text) >= self.config.min_chunk_size:
                    chunks.append(
                        self._make_chunk(
                            title=node.name,
                            content=class_text[: self.config.max_chunk_size],
                            source=rel_path,
                            chunk_type=ChunkType.CODE,
                            line_start=getattr(node, "lineno", 1),
                        )
                    )

                if len(class_text) > self.config.max_chunk_size:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_text = _segment(item)
                            if len(method_text) >= self.config.min_chunk_size:
                                chunks.append(
                                    self._make_chunk(
                                        title=f"{node.name}.{item.name}",
                                        content=method_text[: self.config.max_chunk_size],
                                        source=rel_path,
                                        chunk_type=ChunkType.CODE,
                                        line_start=getattr(item, "lineno", 1),
                                    )
                                )

        return chunks

    def _chunk_python_regex_fallback(
        self,
        source_text: str,
        rel_path: str,
        stem: str,
        lines: list[str],
    ) -> list[Chunk]:
        """Fallback chunking for malformed Python using regex blocks."""
        del source_text, stem
        decls: list[tuple[int, str]] = []
        decl_re = re.compile(
            r"^(?P<indent>[ \t]*)(?:async\s+def|def|class)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
        )

        for idx, line in enumerate(lines):
            match = decl_re.match(line)
            if not match:
                continue
            if match.group("indent"):
                continue
            decls.append((idx, match.group("name")))

        chunks: list[Chunk] = []
        for i, (start_idx, name) in enumerate(decls):
            end_idx = decls[i + 1][0] if i + 1 < len(decls) else len(lines)
            block = "\n".join(lines[start_idx:end_idx]).strip()
            if len(block) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=name,
                        content=block[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.CODE,
                        line_start=start_idx + 1,
                    )
                )

        return chunks

    def _chunk_js_ts_fallback(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Fallback JS/TS chunking using regex heuristics."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(base_path))
        lines = content.splitlines()

        chunks: list[Chunk] = []

        # Imports
        import_lines: list[str] = []
        import_start: int | None = None
        for idx, line in enumerate(lines):
            if line.lstrip().startswith("import "):
                if import_start is None:
                    import_start = idx + 1
                import_lines.append(line)

        if import_lines:
            import_text = "\n".join(import_lines).strip()
            if len(import_text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=f"{Path(rel_path).stem} (imports)",
                        content=import_text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.REFERENCE,
                        line_start=import_start,
                    )
                )

        decls: list[tuple[int, str]] = []
        class_re = re.compile(r"^\s*(?:export\s+)?class\s+(\w+)")
        export_default_re = re.compile(r"^\s*export\s+default\s+function\s+(\w+)")
        func_re = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)")
        arrow_re = re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*=.*=>")

        for idx, line in enumerate(lines):
            name = None
            match = export_default_re.match(line)
            if match:
                name = match.group(1)
            else:
                match = class_re.match(line)
                if match:
                    name = match.group(1)
                else:
                    match = func_re.match(line)
                    if match:
                        name = match.group(1)
                    else:
                        match = arrow_re.match(line)
                        if match:
                            name = match.group(1)

            if name:
                decls.append((idx, name))

        for i, (start_idx, name) in enumerate(decls):
            end_idx = decls[i + 1][0] if i + 1 < len(decls) else len(lines)
            block = "\n".join(lines[start_idx:end_idx]).strip()
            if len(block) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=name,
                        content=block[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.CODE,
                        line_start=start_idx + 1,
                    )
                )

        return chunks

    def _chunk_yaml_fallback(self, file_path: Path, base_path: Path) -> list[Chunk]:
        """Fallback YAML chunking by top-level keys."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(base_path))
        lines = content.splitlines()

        key_positions: list[tuple[int, str]] = []
        key_re = re.compile(r"^([A-Za-z0-9_-]+)\s*:")
        for idx, line in enumerate(lines):
            if line.startswith(" "):
                continue
            match = key_re.match(line)
            if match:
                key_positions.append((idx, match.group(1)))

        chunks: list[Chunk] = []
        for i, (start_idx, key) in enumerate(key_positions):
            end_idx = key_positions[i + 1][0] if i + 1 < len(key_positions) else len(lines)
            block = "\n".join(lines[start_idx:end_idx]).strip()
            if len(block) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=key,
                        content=block[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.REFERENCE,
                        line_start=start_idx + 1,
                    )
                )

        return chunks

    # Python chunking

    def _chunk_python(self, root: Node, source: bytes, rel_path: str) -> list[Chunk]:
        """Extract Python chunks: module docstring, imports, classes, functions."""
        chunks: list[Chunk] = []

        import_lines: list[str] = []
        import_start: int | None = None

        for child in root.children:
            if child.type in ("import_statement", "import_from_statement"):
                if import_start is None:
                    import_start = child.start_point[0] + 1
                import_lines.append(_node_text(child, source))
            elif child.type == "expression_statement" and not chunks and not import_lines:
                # Module docstring (first expression_statement before anything else)
                text = _node_text(child, source).strip()
                if text.startswith(('"""', "'''")):
                    docstring = text.strip("\"' \n")
                    if len(docstring) >= self.config.min_chunk_size:
                        chunks.append(
                            self._make_chunk(
                                title=f"{Path(rel_path).stem} (module)",
                                content=docstring[: self.config.max_chunk_size],
                                source=rel_path,
                                chunk_type=ChunkType.CONCEPT,
                                line_start=child.start_point[0] + 1,
                            )
                        )

        if import_lines:
            import_text = "\n".join(import_lines)
            if len(import_text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=f"{Path(rel_path).stem} (imports)",
                        content=import_text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.REFERENCE,
                        line_start=import_start,
                    )
                )

        for child in root.children:
            if child.type == "function_definition":
                chunks.append(self._python_function_chunk(child, source, rel_path))
            elif child.type == "class_definition":
                chunks.extend(self._python_class_chunks(child, source, rel_path))
            elif child.type == "decorated_definition":
                # Decorated functions/classes
                inner = _decorated_inner(child)
                if inner and inner.type == "function_definition":
                    chunks.append(self._python_function_chunk(child, source, rel_path))
                elif inner and inner.type == "class_definition":
                    chunks.extend(self._python_class_chunks(child, source, rel_path))

        return chunks

    def _python_function_chunk(self, node: Node, source: bytes, rel_path: str) -> Chunk:
        """Create a chunk from a Python function definition."""
        func_node = node
        if node.type == "decorated_definition":
            inner = _decorated_inner(node)
            if inner:
                func_node = inner

        name = _child_by_field(func_node, "name")
        func_name = _node_text(name, source) if name else "unknown"
        text = _node_text(node, source)  # keep decorators in content

        return self._make_chunk(
            title=func_name,
            content=text[: self.config.max_chunk_size],
            source=rel_path,
            chunk_type=ChunkType.CODE,
            line_start=node.start_point[0] + 1,
        )

    def _python_class_chunks(self, node: Node, source: bytes, rel_path: str) -> list[Chunk]:
        """Create chunks from a Python class definition.

        Small classes become a single chunk. Large classes are split:
        one chunk for the class signature + docstring, then one per method.
        """
        class_node = node
        if node.type == "decorated_definition":
            inner = _decorated_inner(node)
            if inner:
                class_node = inner

        name = _child_by_field(class_node, "name")
        class_name = _node_text(name, source) if name else "unknown"
        full_text = _node_text(node, source)

        # If the whole class fits in one chunk, keep it together
        if len(full_text) <= self.config.max_chunk_size:
            return [
                self._make_chunk(
                    title=class_name,
                    content=full_text,
                    source=rel_path,
                    chunk_type=ChunkType.CODE,
                    line_start=node.start_point[0] + 1,
                )
            ]

        # Otherwise, split into class header + individual methods
        chunks: list[Chunk] = []
        body = _child_by_field(class_node, "body")
        methods: list[Node] = []

        if body:
            for child in body.children:
                if child.type in ("function_definition", "decorated_definition"):
                    methods.append(child)

        # Class header (everything before first method)
        if methods:
            header_end = methods[0].start_byte
            header_text = (
                source[node.start_byte : header_end].decode("utf-8", errors="replace").rstrip()
            )
            if len(header_text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=class_name,
                        content=header_text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.CODE,
                        line_start=node.start_point[0] + 1,
                    )
                )

        # Each method
        for method_node in methods:
            inner = method_node
            if method_node.type == "decorated_definition":
                found = _decorated_inner(method_node)
                if found:
                    inner = found

            method_name = _child_by_field(inner, "name")
            mname = _node_text(method_name, source) if method_name else "unknown"
            method_text = _node_text(method_node, source)

            if len(method_text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=f"{class_name}.{mname}",
                        content=method_text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.CODE,
                        line_start=method_node.start_point[0] + 1,
                    )
                )

        return (
            chunks
            if chunks
            else [
                self._make_chunk(
                    title=class_name,
                    content=full_text[: self.config.max_chunk_size],
                    source=rel_path,
                    chunk_type=ChunkType.CODE,
                    line_start=node.start_point[0] + 1,
                )
            ]
        )

    # JavaScript / TypeScript chunking

    def _chunk_js_ts(self, root: Node, source: bytes, rel_path: str) -> list[Chunk]:
        """Extract JS/TS chunks: imports, exports, classes, functions."""
        chunks: list[Chunk] = []
        import_lines: list[str] = []
        import_start: int | None = None

        for child in root.children:
            if child.type == "import_statement":
                if import_start is None:
                    import_start = child.start_point[0] + 1
                import_lines.append(_node_text(child, source))
                continue

            # export_statement wraps classes, functions, etc.
            inner = child
            if child.type == "export_statement":
                for sub in child.children:
                    if sub.type in (
                        "class_declaration",
                        "function_declaration",
                        "lexical_declaration",
                        "abstract_class_declaration",
                    ):
                        inner = sub
                        break

            if inner.type in ("class_declaration", "abstract_class_declaration"):
                name_node = _child_by_field(inner, "name")
                name = _node_text(name_node, source) if name_node else "unknown"
                text = _node_text(child, source)  # include `export` keyword
                if len(text) >= self.config.min_chunk_size:
                    chunks.append(
                        self._make_chunk(
                            title=name,
                            content=text[: self.config.max_chunk_size],
                            source=rel_path,
                            chunk_type=ChunkType.CODE,
                            line_start=child.start_point[0] + 1,
                        )
                    )

            elif inner.type == "function_declaration":
                name_node = _child_by_field(inner, "name")
                name = _node_text(name_node, source) if name_node else "unknown"
                text = _node_text(child, source)
                if len(text) >= self.config.min_chunk_size:
                    chunks.append(
                        self._make_chunk(
                            title=name,
                            content=text[: self.config.max_chunk_size],
                            source=rel_path,
                            chunk_type=ChunkType.CODE,
                            line_start=child.start_point[0] + 1,
                        )
                    )

            elif inner.type == "lexical_declaration":
                # const foo = (...) => { ... }
                name = self._extract_js_declaration_name(inner, source)
                text = _node_text(child, source)
                if len(text) >= self.config.min_chunk_size:
                    chunks.append(
                        self._make_chunk(
                            title=name,
                            content=text[: self.config.max_chunk_size],
                            source=rel_path,
                            chunk_type=ChunkType.CODE,
                            line_start=child.start_point[0] + 1,
                        )
                    )

        if import_lines:
            import_text = "\n".join(import_lines)
            if len(import_text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=f"{Path(rel_path).stem} (imports)",
                        content=import_text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.REFERENCE,
                        line_start=import_start,
                    )
                )

        return chunks

    def _extract_js_declaration_name(self, node: Node, source: bytes) -> str:
        """Extract variable name from a lexical_declaration (const x = ...)."""
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = _child_by_field(child, "name")
                if name_node:
                    return _node_text(name_node, source)
        return Path("unknown").stem

    # YAML chunking

    def _chunk_yaml(self, root: Node, source: bytes, rel_path: str) -> list[Chunk]:
        """Extract YAML chunks by top-level mapping pairs."""
        chunks: list[Chunk] = []
        mapping = self._find_top_level_mapping(root)
        if mapping is None:
            # No mapping found, treat whole file as one chunk
            text = source.decode("utf-8", errors="replace").strip()
            if len(text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=Path(rel_path).stem,
                        content=text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.REFERENCE,
                        line_start=1,
                    )
                )
            return chunks

        for child in mapping.children:
            if child.type != "block_mapping_pair":
                continue

            # Key is the first flow_node child
            key_text = ""
            for sub in child.children:
                if sub.type == "flow_node":
                    key_text = _node_text(sub, source).strip()
                    break

            pair_text = _node_text(child, source)
            if len(pair_text) >= self.config.min_chunk_size:
                chunks.append(
                    self._make_chunk(
                        title=key_text or Path(rel_path).stem,
                        content=pair_text[: self.config.max_chunk_size],
                        source=rel_path,
                        chunk_type=ChunkType.REFERENCE,
                        line_start=child.start_point[0] + 1,
                    )
                )

        return chunks

    def _find_top_level_mapping(self, node: Node) -> Node | None:
        """Find the top-level block_mapping in a YAML tree."""
        # stream → document → block_node → block_mapping
        cursor = node
        for expected in ("stream", "document", "block_node", "block_mapping"):
            found = None
            if cursor.type == expected:
                found = cursor
            else:
                for child in cursor.children:
                    if child.type == expected:
                        found = child
                        break
            if found is None:
                return None
            cursor = found
        return cursor

    # Parser management

    def _get_parser(self, lang_name: str) -> object | None:
        """Get or create a tree-sitter Parser for the given language.

        Returns None if tree-sitter or the grammar is unavailable.
        """
        if lang_name in self._parsers:
            cached = self._parsers[lang_name]
            if cached is _NO_PARSER or cached is None:
                return None
            return cached

        try:
            from tree_sitter import Language, Parser
        except ImportError:
            logger.debug("tree-sitter not installed, falling back to regex chunker")
            self._parsers[lang_name] = _NO_PARSER  # type: ignore[assignment]
            return None

        spec = _LANGUAGE_SPECS.get(lang_name)
        if spec is None:
            return None

        try:
            # Dynamic import: "tree_sitter_python.language" → module.function()
            module_path, func_name = spec.loader.rsplit(".", 1)
            import importlib

            mod = importlib.import_module(module_path)
            lang_func = getattr(mod, func_name)
            language = Language(lang_func())
            parser = Parser(language)
            self._parsers[lang_name] = parser
            return parser
        except (ImportError, AttributeError, Exception) as e:
            logger.debug("Failed to load %s grammar: %s", lang_name, e)
            self._parsers[lang_name] = _NO_PARSER  # type: ignore[assignment]
            return None


# Node helpers


def _node_text(node: Node, source: bytes) -> str:
    """Extract text content from a tree-sitter node."""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _child_by_field(node: Node, field_name: str) -> Node | None:
    """Get a child node by field name."""
    return node.child_by_field_name(field_name)


def _decorated_inner(node: Node) -> Node | None:
    """Get the inner definition from a decorated_definition node."""
    for child in node.children:
        if child.type in ("function_definition", "class_definition"):
            return child
    return None
