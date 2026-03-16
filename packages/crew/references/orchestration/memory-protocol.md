# Memory Protocol

Cross-session memory for pixl-crew agents. Primary storage is the pixl DB (`.pixl/pixl.db`) with file-based fallback in `.claude/memory/`.

## Storage

All session memory is stored in the pixl DB when available:

| Data | Artifact Type | CLI Command |
|------|--------------|-------------|
| Decisions | `decision` | `pixl artifact put --name decision-<topic> --type decision` |
| Session summaries | `session_summary` | `pixl artifact put --name session-summary-<ts> --type session_summary` |
| Instincts | `instinct` | `pixl artifact put --name instinct-<id> --type instinct` |
| Costs | `cost_log` | `pixl artifact put --name cost-<session> --type cost_log` |
| Tool usage | `tool_usage` | `pixl artifact put --name tool-usage-<ts> --type tool_usage` |
| Task state | `task_state` | `pixl artifact put --name task-state --type task_state` |
| Pre-compact snapshots | `compact_snapshot` | `pixl artifact put --name pre-compact-<ts> --type compact_snapshot` |

## Reading Memory

On SessionStart, the hook reads from the DB:

```bash
pixl artifact search --query "session-summary" --type session_summary --limit 3
pixl artifact search --query "decision" --type decision --limit 10
```

This gives agents enough context to continue work without overwhelming the context window.

## Decision Log Format

Each decision is stored as a JSON artifact:

```json
{
  "date": "2025-01-15",
  "category": "architecture",
  "what": "Use CQRS for billing service",
  "why": "Read/write models differ significantly",
  "context": "billing"
}
```

## When to Log Decisions

Agents should log decisions when:

1. **Architectural choices** — technology selection, pattern adoption, module boundaries
2. **Convention establishment** — naming patterns, file organization, API design choices
3. **Issue resolution** — root cause findings, workarounds adopted, bugs fixed with non-obvious solutions
4. **Dependency decisions** — library selection, version pinning rationale

Do NOT log:

- Routine implementation choices (variable names, formatting)
- Decisions already captured in CLAUDE.md
- Temporary debugging steps

## Session Summary Format

Summaries are written automatically by `stop-summary.sh` and include:

- Branch name and recent commits
- Files changed (git diff stats)
- Modified files list
- Task state reference (if applicable)

## Fallback

When pixl is not installed, file-based persistence in `.claude/memory/` is used:

```
.claude/memory/
├── decisions.jsonl          # Append-only decision log
├── instincts.jsonl          # Learned patterns from /continuous-learning
├── costs.jsonl              # Per-session token costs
├── tool-usage.jsonl         # Tool usage patterns
└── sessions/
    └── YYYY-MM-DD-HH-MM.md # Per-session summaries
```

The SessionStart hook detects which storage is available and reads from the appropriate source.

## Integration Reference

See `references/intel/cli-integration.md` for the full CLI integration contract, artifact type taxonomy, and env var bridge documentation.
