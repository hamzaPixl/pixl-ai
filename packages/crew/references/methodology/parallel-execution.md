# Parallel Execution

## When to Parallelize

Tasks are safe to parallelize when they have:
- No shared dependencies
- No overlapping file modifications
- Independently verifiable results
- Clear benefit from concurrency

## Good Candidates

- Independent features touching different files
- Separate test suites
- Different file types (docs vs code vs config)
- Independent refactors in isolated modules

## Bad Candidates (Keep Sequential)

- Dependent features (B needs A's output)
- Changes to the same files
- Database migrations
- Build → test → deploy chains

## Decision Flow

1. List all tasks
2. For each pair, ask: Same files? Depends on output?
3. Group parallel-safe tasks together
4. Dispatch concurrently

## Execution Process

### 1. Identify and Categorize
Analyze task dependencies. Map which files each task touches.

### 2. Dispatch in Parallel
Each agent needs:
- **Complete context** — all relevant background
- **Clear success criteria** — what "done" looks like
- **Specific files** — exactly which files to modify
- **Boundaries** — what NOT to touch

### 3. Monitor Without Interference
Let agents work independently. Don't intervene unless blocked.

### 4. Integrate Results
- Check for file conflicts between agents
- Run full test suite
- Verify build succeeds

## Agent Context Template

```markdown
## Task: [description]

**Files to modify:**
- path/to/file1.ts
- path/to/file2.ts

**DO NOT modify:**
- path/to/shared/config.ts
- path/to/other-feature/

**Success criteria:**
- [ ] Tests pass
- [ ] No lint errors
- [ ] Feature works as described
```

## Limits

- **2-3 parallel tasks** is ideal
- **4+** tasks: consider batching into waves
- Each task must be independently completable

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Parallelizing dependent tasks | Race conditions, conflicts | Sequence dependent tasks |
| Too many agents at once | Context overload, conflicts | Batch into 2-3 per wave |
| Insufficient context per agent | Agents make wrong assumptions | Provide complete context |
| No integration plan | Conflicts discovered late | Plan integration step upfront |
| Shared file modifications | Merge conflicts guaranteed | Assign files exclusively |

## Output Format

```markdown
## Parallel Execution Plan

### Wave 1 (parallel)
- **Agent A:** [task] — files: [list]
- **Agent B:** [task] — files: [list]

### Wave 2 (after Wave 1)
- **Agent C:** [task, depends on A] — files: [list]

### Integration
- Run full test suite
- Verify build
- Check for conflicts
```
