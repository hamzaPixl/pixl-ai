# Context Management

## When to Compact

- Use `/compact` or `/clear` when context exceeds ~60% of the window
- Compact before starting a new, unrelated task
- The PreCompact hook preserves critical session state automatically

## Subagent Delegation

- Use Explore agents for codebase searches that may require 3+ queries
- Use `isolation: "worktree"` for agents that modify files independently
- Use `run_in_background: true` for independent research while continuing other work

## Skill Routing

- Claude routes skills by semantic matching on descriptions — not by keyword
- If a skill doesn't trigger, the description may need a "Use when..." clause
- Check `skills/ROUTING.md` for the decision tree before building ad-hoc workflows

## Context Budget

- Skill descriptions (~100 words each × 75 skills) consume ~7.5K tokens at session start
- Shorter descriptions free routing context for actual work
- Move detailed trigger lists into SKILL.md body, keep description to 1-2 sentences

## Token Budget

- Before large refactors (>5 files), clean dead imports/exports/props first — commit separately to reduce token waste
- Keep refactor phases under 5 files to minimize compaction risk
- When RTK is installed, Bash outputs are compressed 60-90% automatically — prefer Bash commands over raw tool output for large results
- For long sessions: use `/strategic-compact` proactively rather than waiting for auto-compaction

## CLAUDE.md Sizing

- Project CLAUDE.md should be concise — aim for under 60 lines of actionable instructions
- Move detailed methodology, patterns, and trigger lists into skills or references
- Hand-craft CLAUDE.md content — LLM-generated instructions can hurt agent performance (ETH Zurich study)
- Use `/claude-md` skill for structured generation, but always review and trim the output
