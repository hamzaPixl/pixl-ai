# Git Worktrees

Best practices for using git worktrees with Claude Code and pixl-crew.

## When to Use Worktrees

- **Parallel features**: Work on multiple features simultaneously without stashing
- **Batch operations**: Apply the same change across many modules (see `/batch` skill)
- **Isolated experiments**: Try an approach without affecting your main working tree
- **Long-running agents**: Let a subagent modify files without conflicting with your session

## Claude Code Native Support

```bash
# Start a session in a new worktree
claude --worktree feat/auth

# Creates .claude/worktrees/feat-auth/ with a full repo copy
# Auto-cleanup on exit — prompts to keep/remove if changes exist
```

## Subagent Isolation

Use `isolation: "worktree"` when spawning agents that modify files independently:

```
Agent(
  description: "Implement auth module",
  prompt: "...",
  isolation: "worktree"
)
```

The agent gets its own repo copy. If it makes changes, the worktree path and branch are returned in the result. If no changes are made, the worktree is auto-cleaned.

**When to use isolation:**
- Agent will write/edit files that overlap with your current work
- Multiple agents run in parallel and may touch the same files
- You want to review agent changes before merging into your branch

**When NOT to use isolation:**
- Agent is read-only (exploration, analysis)
- Agent modifies files you're not currently touching
- Single agent doing sequential work

## Integration with /batch

The `/batch` skill uses worktree isolation by default when processing independent units:

```
/batch "Add error handling to all route handlers"
```

Each unit gets its own worktree, runs in parallel, and results are merged or opened as separate PRs.

## .gitignore Setup

Add the worktrees directory to `.gitignore`:

```
.claude/worktrees/
```

## Workflow Patterns

### Parallel Feature Development

1. Start main feature in your session
2. Spawn worktree-isolated agents for independent sub-features
3. Review each agent's branch, merge into your feature branch

### Safe Refactoring

1. Create a worktree for the refactor
2. Run tests in the worktree to verify
3. Merge only if tests pass — main tree stays clean

### Code Review + Fix

1. Reviewer agent runs in main tree (read-only)
2. Fixer agents spawn in worktrees for each finding
3. Each fix is a separate branch for easy review
