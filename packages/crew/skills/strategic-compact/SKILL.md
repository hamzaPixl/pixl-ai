---
name: strategic-compact
description: "Guide intelligent context compaction — identify what to preserve, what to summarize, and what to discard before hitting context limits. Use when context is getting large, before /compact, or when asked to manage context window."
allowed-tools: Read, Glob, Grep
argument-hint: "[--preserve=files|decisions|tasks]"
context: fork
---

# Strategic Compact

Guide intelligent context management before compaction.

## Step 1: Assess Current Context

Identify what's currently in the context window:
- Files read (which ones, how recently)
- Decisions made (architectural choices, trade-offs)
- Active tasks (what's in progress, what's done)
- Tool call history (what's been tried, what worked)

## Step 2: Classify by Retention Priority

| Priority     | What                                         | Action        |
| ------------ | -------------------------------------------- | ------------- |
| **Must keep** | Current task description and acceptance criteria | Preserve     |
| **Must keep** | Architectural decisions made this session     | Preserve     |
| **Must keep** | Error messages and their resolutions         | Preserve     |
| **Should keep** | File paths and key line numbers            | Summarize     |
| **Should keep** | API contracts and type definitions          | Summarize     |
| **Can discard** | Full file contents already edited          | Discard       |
| **Can discard** | Search results from completed lookups      | Discard       |
| **Can discard** | Tool call metadata and verbose outputs     | Discard       |

## Step 3: Generate Compact Summary

Create a compact state document:

```markdown
## Active Task
<1-2 sentence description of what we're doing>

## Key Decisions
- <decision 1>
- <decision 2>

## Files Modified
- `path/to/file.ts` — <what was changed>

## Blocked On / Next Steps
- <what needs to happen next>

## Important Context
- <any critical information that would be lost>
```

## Step 4: Recommend Action

Based on context usage, recommend:
- **Continue** — context is fine, no action needed
- **Summarize** — compress verbose outputs, keep key facts
- **Save and clear** — run `/session-wrap` then `/clear`
- **Delegate** — offload remaining work to a subagent with a context packet

## Output

Present the compact summary and recommendation. If the user approves, save to `.claude/memory/pre-compact-<timestamp>.md`.
