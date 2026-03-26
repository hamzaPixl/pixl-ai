# CLI ↔ Plugin Integration

The pixl CLI (`.pixl/pixl.db`) is the single source of truth for all session data. The plugin writes to and reads from the DB via CLI commands, with file-based persistence as a fallback when pixl is not installed.

## Environment Variables

When running inside `pixl workflow run`, these env vars are set automatically:

| Var | Purpose |
|-----|---------|
| `PIXL_SESSION_ID` | Auto-tags artifacts to current session |
| `PIXL_STAGE_ID` | Auto-tags artifacts to current DAG stage |
| `PIXL_STORAGE_PROJECT` | Overrides cwd-based project detection |

No need to pass `--session` flags — the CLI reads these automatically.

## Detection Pattern

All hook scripts source `_pixl-detect.sh` (via `_common.sh`) which provides:

```bash
PIXL_AVAILABLE=false|true     # whether pixl binary is on PATH
PIXL_IN_WORKFLOW=false|true   # whether PIXL_SESSION_ID is set
pixl_put <name> <type> <content>   # store artifact (no-op if unavailable)
pixl_get <name>                     # retrieve artifact content
pixl_search <query> <type> <limit>  # search artifacts
```

Auto-init: if pixl is available but `.pixl/` doesn't exist, `pixl project init` runs automatically.

## Artifact Types

| Type | Purpose | Written by |
|------|---------|------------|
| `session_summary` | Per-session git diff stats and modified files | `stop-summary.sh` |
| `decision` | Architectural and workflow decisions | `session-wrap`, `log-pr-url.sh`, agents |
| `cost_log` | Per-session token usage and cost estimates | `cost-tracker.sh` |
| `instinct` | Learned patterns and heuristics | `continuous-learning` |
| `tool_usage` | Tool usage metadata for pattern analysis | `observe-patterns.sh` |
| `compact_snapshot` | Pre-compaction session state snapshot | `pre-compact.sh` |
| `task_state` | Serialized task list for cross-session resume | `task-persist` |
| `test_result` | Test suite results | `qa-engineer` |
| `context_packet` | Structured context for agent delegation | `orchestrator` |

## CLI Commands for Agents

### Store artifacts
```bash
pixl artifact put --name <name> --type <type> --content '<json>'
```

### Retrieve artifacts
```bash
pixl artifact get --name <name> --json
pixl artifact search --query <query> --type <type> --limit N --json
```

### Knowledge search
```bash
pixl knowledge search "<query>" --limit 10 --json
pixl knowledge context "<query>" --max-tokens 4000
```

### Events
```bash
pixl events --type decision --limit 20 --json
pixl event-stats --json
```

## Graceful Degradation

When pixl is not installed:

- **Hooks**: Fall back to `.claude/memory/` flat files (JSONL, markdown)
- **Skills**: Continue with standard file I/O — no CLI commands executed
- **Agents**: Use Glob/Grep instead of `pixl knowledge search`

The integration is additive — all features work without pixl, but gain queryability, cross-session search, and workflow tracking when pixl is present.

## Data Flow

```
[Hook/Agent/Skill] → pixl artifact put → .pixl/pixl.db (SQLite)
                                        ↓
[SessionStart hook] ← pixl artifact search ← .pixl/pixl.db
                                        ↓
[Next session] sees decisions, summaries, instincts from DB
```
