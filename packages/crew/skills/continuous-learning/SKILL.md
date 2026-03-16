---
name: continuous-learning
description: "Instinct-based learning integrated with pixl-crew memory. Observes patterns across sessions, records instincts (heuristics), and applies them to future tasks. Use when asked to learn from mistakes, record a pattern, review instincts, or improve future performance."
allowed-tools: Read, Write, Edit, Glob, Grep
argument-hint: "<action: observe|record|review|apply> [description]"
---

# Continuous Learning

Pattern-based learning that persists across sessions via `.claude/memory/instincts.jsonl`.

## Actions

### `observe` — Analyze Current Session

1. Review the conversation for:
   - Mistakes made and corrected
   - Patterns that worked well
   - User corrections or preferences
   - Repeated actions that could be automated

2. For each observation, draft an instinct:
```json
{
  "timestamp": "2026-03-08T14:30:00Z",
  "trigger": "when editing React components with state",
  "instinct": "always check if the component needs useCallback for handlers passed to children",
  "confidence": 0.7,
  "source": "user corrected missing useCallback in OrderList component",
  "category": "react"
}
```

3. Present observations to user for confirmation before recording.

### `record` — Save a Specific Instinct

Accept a description and create an instinct entry:
1. Parse the description into trigger + instinct + category
2. Set initial confidence to 0.5
3. Append to `.claude/memory/instincts.jsonl`
4. If pixl is available, also persist as a pixl artifact:
   ```bash
   pixl artifact put --name "instinct-<category>-$(date +%s)" --type instinct --content '<json>'
   ```

### `review` — Review and Prune Instincts

1. Read all instincts from `.claude/memory/instincts.jsonl`
2. Group by category
3. Identify:
   - Contradicting instincts (flag for resolution)
   - Low-confidence instincts (< 0.3, suggest removal)
   - Redundant instincts (merge)
   - Stale instincts (not applied in 30+ days)
4. Present summary and recommendations

### `apply` — Load Relevant Instincts

1. Read `.claude/memory/instincts.jsonl`
2. Filter instincts relevant to the current task (by category, trigger keywords)
3. Boost confidence for instincts that match (+0.1)
4. Present applicable instincts as reminders

## Instinct Schema

```jsonl
{"timestamp":"...","trigger":"when...","instinct":"always/never/prefer...","confidence":0.5,"source":"...","category":"...","last_applied":"..."}
```

## Categories

- `react` — React/Next.js patterns
- `typescript` — TypeScript specifics
- `python` — Python patterns
- `testing` — Test writing patterns
- `git` — Version control habits
- `architecture` — Design decisions
- `performance` — Optimization patterns
- `security` — Security practices
- `workflow` — Process and workflow
- `project-specific` — Current project customs

## Integration with Memory Protocol

Instincts complement the existing memory system:
- `decisions.jsonl` — records WHAT was decided
- `instincts.jsonl` — records HOW to approach similar decisions
- `sessions/` — records WHAT happened
