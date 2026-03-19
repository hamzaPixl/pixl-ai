---
name: intel
description: "Semantic code search (FTS5-indexed, BM25-ranked), artifact CRUD, and event history via the pixl CLI. Use when you need ranked search results, fuzzy code discovery, or artifact/event log queries. Falls back to Grep/Glob when pixl CLI is not installed."
allowed-tools: Bash, Read, Grep, Glob
argument-hint: "<query or command — e.g. 'search auth middleware', 'build index', 'artifact get session-plan', 'events --type decision'>"
---

# Intel — Unified Intelligence Queries

Query the pixl knowledge base for AST-indexed code search, artifacts, events, and dependency graphs. Falls back to Glob/Grep when pixl is not available.

## Availability Check

Before running any `pixl` command, verify availability:

```bash
if command -v pixl &>/dev/null; then
  # pixl available — use it
else
  # Fall back to Glob/Grep
fi
```

If pixl is not available, use Glob and Grep tools directly as fallback. Inform the user that pixl is not installed and results come from basic file search.

## Commands

### Knowledge Search (primary use case)

Search AST-indexed code with FTS5 + BM25 scoring:

```bash
pixl knowledge search "QUERY" --limit 10 --json
pixl knowledge search "QUERY" --scope "*.tsx" --json        # filter by file pattern
pixl knowledge search "QUERY" --type code --json            # code only
pixl knowledge search "QUERY" --type doc --json             # docs only
```

**Fallback**: Use Grep with the query pattern across the codebase.

### Context Building

Build token-aware context for a query (useful for feeding into agents):

```bash
pixl knowledge context "QUERY" --max-tokens 4000
```

### Index Management

```bash
pixl knowledge status --json          # check index freshness
pixl knowledge build --code           # rebuild code index only
pixl knowledge build --full           # full rebuild (code + docs)
```

### Artifacts

Store and retrieve versioned, searchable artifacts:

```bash
pixl artifact get --name NAME --json
pixl artifact put --name NAME --content "..." --json
pixl artifact search --query Q --json
pixl artifact versions SESSION ARTIFACT --json
```

### Events & History

```bash
pixl events --type TYPE --limit N --json    # TYPE: decision, error, milestone, etc.
pixl event-stats --json                      # aggregate event statistics
```

### State & Dependencies

```bash
pixl state show ENTITY_ID                   # show entity state
pixl state graph EPIC_ID --json             # dependency graph for an epic
pixl state deps FEATURE_ID                  # dependencies for a feature
```

## Workflow

1. **Parse the user's request** — determine which command category applies
2. **Check pixl availability** — run the availability check
3. **Execute the command** — use `--json` output for structured results
4. **Format results** — present findings with file paths and line numbers
5. **Fall back if needed** — if pixl is unavailable, use Glob/Grep and note the limitation

## Examples

**User**: "Search for authentication middleware"
→ `pixl knowledge search "authentication middleware" --limit 10 --json`

**User**: "Find all React components that use useAuth"
→ `pixl knowledge search "useAuth" --scope "*.tsx" --type code --json`

**User**: "Store this session plan as an artifact"
→ `pixl artifact put --name session-plan --content "..." --json`

**User**: "What decisions were made recently?"
→ `pixl events --type decision --limit 20 --json`

**User**: "Show dependency graph for the billing epic"
→ `pixl state graph billing-epic --json`

**User**: "Rebuild the code index"
→ `pixl knowledge build --code`
