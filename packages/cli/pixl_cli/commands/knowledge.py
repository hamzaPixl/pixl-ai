"""pixl knowledge — search, build, status, context.

Delegates to engine's KnowledgeIndex, KnowledgeSearch, and ContextBuilder.
"""

from __future__ import annotations

import click

from pixl_cli._output import emit_error, emit_json
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def knowledge(ctx: click.Context) -> None:
    """Knowledge index — search, build, and status."""


@knowledge.command("search")
@click.argument("query")
@click.option("--limit", default=5, type=int, help="Max results.")
@click.option("--scope", default=None, help="File pattern filter (e.g., '*.tsx').")
@click.option("--type", "chunk_type", default=None, help="Chunk type filter (code, doc, concept).")
@click.pass_context
def knowledge_search(
    ctx: click.Context,
    query: str,
    limit: int,
    scope: str | None,
    chunk_type: str | None,
) -> None:
    """Search the knowledge index."""
    from pixl.knowledge import KnowledgeSearch

    cli = get_ctx(ctx)
    searcher = KnowledgeSearch(cli.project_path)

    chunk_types_list = None
    if chunk_type:
        from pixl.models.knowledge import ChunkType

        try:
            chunk_types_list = [ChunkType(chunk_type)]
        except ValueError:
            chunk_types_list = None

    results = searcher.search(
        query=query,
        limit=limit,
        chunk_types=chunk_types_list,
        scope=scope,
    )

    if cli.is_json:
        emit_json([r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in results])
    else:
        if not results:
            click.echo("No results found.")
            return
        for i, r in enumerate(results, 1):
            score = getattr(r, "score", "?")
            source = getattr(r, "source", "?")
            title = getattr(r, "title", "?")
            content = getattr(r, "content", "")
            click.echo(f"\n--- Result {i} (score: {score}) ---")
            click.echo(f"  Source: {source}")
            click.echo(f"  Title:  {title}")
            if len(content) > 300:
                content = content[:300] + "..."
            click.echo(f"  {content}")


@knowledge.command("build")
@click.option("--code", "include_code", is_flag=True, default=False, help="Index source code files.")
@click.option("--full", "full_rebuild", is_flag=True, default=False, help="Force full rebuild.")
@click.pass_context
def knowledge_build(ctx: click.Context, include_code: bool, full_rebuild: bool) -> None:
    """Build or rebuild the knowledge index."""
    from pixl.knowledge import KnowledgeIndex

    cli = get_ctx(ctx)
    index = KnowledgeIndex(cli.project_path)

    chunks_created, files_processed = index.build(
        full_rebuild=full_rebuild,
        include_code=include_code,
    )

    result = {
        "files_indexed": files_processed,
        "chunks_created": chunks_created,
        "include_code": include_code,
        "full_rebuild": full_rebuild,
    }

    if cli.is_json:
        emit_json(result)
    else:
        if chunks_created == 0 and files_processed == 0:
            click.echo("No changes detected. Use --full to force rebuild.")
        else:
            click.echo(f"Indexed {files_processed} files, {chunks_created} chunks")


@knowledge.command("status")
@click.pass_context
def knowledge_status(ctx: click.Context) -> None:
    """Show knowledge index status."""
    cli = get_ctx(ctx)
    status = cli.db.knowledge.get_status()

    if cli.is_json:
        emit_json(status)
    else:
        click.echo("Knowledge Index Status:")
        for key, value in status.items():
            click.echo(f"  {key}: {value}")


@knowledge.command("context")
@click.argument("query")
@click.option("--max-tokens", default=4000, type=int, help="Max tokens for context window.")
@click.pass_context
def knowledge_context(ctx: click.Context, query: str, max_tokens: int) -> None:
    """Build a token-aware context string from the knowledge index."""
    from pixl.knowledge import ContextBuilder

    cli = get_ctx(ctx)
    builder = ContextBuilder(cli.project_path)
    context_str = builder.build_context(query=query, max_tokens=max_tokens)

    if cli.is_json:
        emit_json({"query": query, "max_tokens": max_tokens, "context": context_str})
    else:
        click.echo(context_str)
