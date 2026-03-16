# Drift Detection

Strategies for detecting and classifying changes between PRD versions.

## Snapshot Diffing

### 1. Comparing Requirement Sets

When a new PRD is provided and a previous `requirements.json` exists:

1. **Load both versions**: previous requirements (from stored file) and new decomposition
2. **Match by ID**: requirements with the same `id` in both versions
3. **Classify changes**:

| Change Type | Detection Rule |
|------------|---------------|
| `added` | ID exists in new but not in previous |
| `removed` | ID exists in previous but not in new |
| `changed` | Same ID, different `summary` or `acceptance_criteria` |
| `reprioritized` | Same ID, different `priority` |
| `unchanged` | Same ID, same summary, criteria, and priority |

### 2. Handling ID Renumbering

If the new PRD doesn't preserve requirement IDs:

1. Use fuzzy matching on `summary` text (>80% similarity → likely same requirement)
2. Flag ambiguous matches for user confirmation
3. Treat unmatched items as added/removed

### 3. Drift Entry Format

Each drift entry is appended to `.context/spec/drift-log.jsonl`:

```jsonl
{"timestamp":"2026-03-15T14:00:00Z","type":"added","id":"R-026","summary":"Admin can export user data as CSV","priority":"should"}
{"timestamp":"2026-03-15T14:00:00Z","type":"removed","id":"R-012","summary":"Support for IE11 browser","priority":"could"}
{"timestamp":"2026-03-15T14:00:00Z","type":"changed","id":"R-005","field":"acceptance_criteria","before":["Email validation"],"after":["Email validation","Domain allowlist"]}
{"timestamp":"2026-03-15T14:00:00Z","type":"reprioritized","id":"R-008","before":"could","after":"must"}
```

## Drift Classification

### Impact Levels

| Drift Type | Impact | Action Required |
|-----------|--------|-----------------|
| `must` requirement added | High | New tasks needed |
| `must` requirement removed | High | Existing work may be invalidated |
| `must` → `could` reprioritized | Medium | Existing work may be deprioritized |
| `could` → `must` reprioritized | Medium | Existing work needs promotion |
| `should` requirement changed | Medium | Review implementation for alignment |
| `could` requirement added | Low | Track for future sprints |
| `could` requirement removed | Low | No immediate action |

### Integration with /task-plan

When drift is detected, the coverage report can be consumed by `/task-plan` for adaptive replanning:

1. **Added requirements** → generate new tasks
2. **Removed requirements** → mark existing tasks as irrelevant
3. **Changed requirements** → flag existing tasks for review
4. **Reprioritized requirements** → reorder task priority

The drift report includes enough context for `/task-plan` to automatically suggest task adaptations without re-reading the full PRD.

## Checkpoint Timing

The best times to run `/spec-review` are at natural project boundaries:

- **After sprint review**: validate what was built matches sprint goals
- **After PRD update**: detect what changed and impact on current work
- **Before sprint planning**: ensure the plan reflects current requirements
- **After major feature merge**: verify feature completeness
- **At project milestones**: track overall progress toward launch

## Historical Trend Analysis

The `drift-log.jsonl` enables trend analysis over time:

- **Stability score**: ratio of unchanged to total requirements over time
- **Scope growth**: cumulative added vs removed requirements
- **Priority churn**: how often requirements change priority
- **Completion velocity**: coverage percentage growth per sprint
