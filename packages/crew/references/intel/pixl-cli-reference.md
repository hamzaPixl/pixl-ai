# Synq (pixl) CLI Reference for Agents

Quick reference for the most useful `pixl` CLI commands. All commands support `--json` for structured output.

## Availability

```bash
command -v pixl &>/dev/null && [ -d ".pixl" ]
```

If unavailable, fall back to Glob/Grep for code search.

## Code Search (most common)

```bash
pixl knowledge search "QUERY" --limit N --json
pixl knowledge search "QUERY" --scope "*.tsx" --json     # file pattern filter
pixl knowledge search "QUERY" --type code --json         # code only
pixl knowledge search "QUERY" --type doc --json          # docs only
pixl knowledge context "QUERY" --max-tokens 4000         # token-aware context
```

## Index Management

```bash
pixl knowledge status --json       # freshness check
pixl knowledge build --code        # incremental code index
pixl knowledge build --full        # full rebuild
```

## Artifacts

```bash
pixl artifact get --name NAME --json
pixl artifact put --name NAME --content "..." --json
pixl artifact search --query Q --json
pixl artifact versions SESSION ARTIFACT --json
```

## Events

```bash
pixl events --type decision --limit 20 --json
pixl event-stats --json
```

## State & Dependencies

```bash
pixl state show ENTITY_ID
pixl state graph EPIC_ID --json
pixl state deps FEATURE_ID
```

## By Agent Role

| Agent | Most useful commands |
|---|---|
| explorer | `pixl knowledge search` — semantic search alongside Grep |
| backend-engineer | `pixl knowledge search --scope "*.py"` — find Python patterns |
| frontend-engineer | `pixl knowledge search --scope "*.tsx"` — find component patterns |
| qa-engineer | `pixl artifact search` — test artifacts; `pixl event-stats` — failure rates |
| orchestrator | `pixl state graph` — execution order; `pixl knowledge status` — index health |
| tech-lead | `pixl knowledge search` — pattern consistency across codebase |

## Availability (Updated)

Auto-init handles `.pixl/` creation — no need to check for the directory:

```bash
# Before (deprecated):
command -v pixl &>/dev/null && [ -d ".pixl" ]

# After:
command -v pixl &>/dev/null
```

## Workflow Context

When running inside `pixl workflow run`, these env vars are set automatically:

| Var | Purpose |
|-----|---------|
| `PIXL_SESSION_ID` | Auto-tags artifacts to current session |
| `PIXL_STAGE_ID` | Auto-tags artifacts to current DAG stage |
| `PIXL_STORAGE_PROJECT` | Overrides cwd-based project detection |

No need to pass `--session` flags — the CLI reads these automatically.
