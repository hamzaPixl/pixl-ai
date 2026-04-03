# Patterns

## Search Before Write

- **Read before edit** — always read a file before modifying it
- **Grep before creating** — search for existing implementations before writing new ones
- **Check imports** — verify a module/function exists before importing it
- **Explore before building** — scan `skills/`, `studio/stacks/`, and `references/` for existing solutions

## Prefer Existing Patterns

- Match the style of surrounding code — don't introduce new patterns in isolation
- Use existing utility functions before creating new ones
- Follow established naming conventions in the project
- Check for shared types/interfaces before defining duplicates

## Incremental Changes

- Make one logical change at a time, verify it works, then move to the next
- Don't refactor while fixing a bug — separate concerns into separate commits
- Test after each change, not just at the end

## Tool Awareness

- **Large files** — when reading files >500 lines, use `offset` and `limit` to read in chunks. A single Read call caps at 2,000 lines; anything beyond is silently truncated
- **Search truncation** — Grep defaults to 250 results (`head_limit`). If results seem sparse, re-scope to a subdirectory or pass `head_limit: 0` for unlimited
- **LSP over Grep for refactoring** — when renaming functions/types/variables, prefer LSP find-references (`typescript-lsp`, `pyright-lsp`) over Grep. Grep misses dynamic imports, re-exports, string literals, and barrel files
- **Comprehensive rename checklist** (when LSP unavailable) — search separately for: direct calls, type references, string literals containing the name, dynamic imports, re-exports, barrel files, test mocks. Then run tests
