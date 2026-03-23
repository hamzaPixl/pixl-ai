# Ship Milestone — Detailed Workflow

## Phase Checklist

### Assessment Phase
- [ ] Read spec/analysis document fully
- [ ] Launch parallel Explore agents (1-3) to scan implementation
- [ ] For each gap/item: check new files, modified files, test files
- [ ] Reassess: "not started" items are often 70-90% done
- [ ] Identify items to drop (wrong approach, superseded, not needed)
- [ ] Produce revised status table

### Planning Phase
- [ ] Decompose remaining work into S/M tasks (no L tasks)
- [ ] Map dependency graph (blocks/blockedBy)
- [ ] Assign parallel waves (Wave 1: all independent, Wave 2+: dependents)
- [ ] Identify which tasks need background agents vs. direct edits
- [ ] Create task tracking (TaskCreate for each)

### Implementation Phase
- [ ] Start Wave 1 tasks in parallel
- [ ] Use `run_in_background: true` for test-heavy agent work
- [ ] Handle surgical edits (1-2 lines) directly without agents
- [ ] Run tests after each wave: `make test` or `uv run pytest`
- [ ] Mark tasks complete immediately when done
- [ ] Start next wave once blockers clear

### User Testing Phase
- [ ] `command --help` for every new command
- [ ] CRUD cycle test (create, list, get, update, delete)
- [ ] `--json` output mode test
- [ ] Error path test (invalid input, missing config, no connection)
- [ ] Streaming test if applicable
- [ ] Dry-run/simulation test if applicable
- [ ] Record any failures for fixing

### Documentation Phase
Files to check and update:
- [ ] `CHANGELOG.md` — version, feature groups, breaking changes
- [ ] `README.md` (root) — components, CLI table, architecture
- [ ] `USAGE.md` — version, new sections, examples
- [ ] `CLAUDE.md` — structure, stores, commands
- [ ] `packages/*/README.md` — per-package updates
- [ ] Scan for stale version numbers

### Commit Phase
Grouping strategy (4-8 commits, not 20+):
1. **feat(engine): ...** — core engine changes (models, storage, execution)
2. **feat(engine): ...** — storage/schema layer
3. **feat(engine): ...** — execution layer
4. **feat(cli): ...** — CLI commands and clients
5. **feat(package): ...** — new packages (sandbox, etc.)
6. **docs: ...** — all documentation
7. **chore: ...** — cleanup (gitignore, temp files)

Pre-push checklist:
- [ ] `make test` passes (full suite)
- [ ] No temp files staged (PLAN.md, .claude/memory/, build artifacts)
- [ ] `.gitignore` covers generated directories
- [ ] Commit messages follow conventional format
- [ ] Co-Authored-By trailer on all commits

## Anti-Patterns

- **22 micro-commits**: Group logically, not per-file
- **Skipping user testing**: Always test as documented in USAGE.md
- **Docs as afterthought**: Stale docs are worse than no docs
- **Sequential when parallel is possible**: Launch independent agents simultaneously
- **Assuming "not started" means 0%**: Deep-explore first — partial work exists more often than expected
- **Testing only happy paths**: Error paths and edge cases matter
- **Committing build artifacts**: Check `.gitignore` for generated directories

## Scaling

For large milestones (20+ tasks):
- Split into 2-3 shipping sessions
- Ship and push after each session
- Use `/compact` between sessions to manage context
- Each session should leave the codebase in a working state (all tests pass)
