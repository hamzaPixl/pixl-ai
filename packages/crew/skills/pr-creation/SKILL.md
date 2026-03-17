---
name: pr-creation
description: "End-to-end pull request workflow: wrap changes → commit → rebase → changelog → create PR. Use when ready to ship changes as a pull request."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<optional: PR title or description>"
disable-model-invocation: true
---

## Overview

Complete PR creation workflow: analyze changes, wrap into conventional commits, rebase on base branch, generate changelog entries, and create the pull request with a structured description.

**Why small, well-described PRs matter**: PRs under 400 lines get reviewed 3x faster and receive higher-quality feedback. A clear description that explains *why* (not just *what*) helps future readers understand intent when git-blaming months later.

## Required References

Before starting, read these files:

- `references/standards/commit-conventions.md` — commit message format and conventions
- `references/standards/pr-best-practices.md` — PR description structure and review guidelines

## Step 1: Discovery

1. Analyze `git diff` (staged + unstaged changes)
2. Identify the base branch (main/master/develop)
3. Check for existing changelog file
4. Determine commit convention (conventional commits)
5. Identify related issues or tickets

## Step 2: Wrap Changes

1. Group related changes into logical units
2. Stage files that belong together
3. Ensure no unrelated changes are included
4. Check for files that shouldn't be committed (.env, credentials)

## Step 3: Commit

1. Create conventional commit messages (feat/fix/refactor/docs/test/chore)
2. Include scope and description
3. Add body with details if commit is non-trivial
4. Reference issues in footer

## Step 4: Rebase

1. Fetch latest base branch
2. Rebase feature branch on base
3. Resolve any merge conflicts
4. Verify tests still pass after rebase

## Step 5: Changelog (Conditional)

**Only if changelog file exists.**

1. Generate changelog entries from commits
2. Follow existing changelog format
3. Group by type (Added, Changed, Fixed, Removed)

## Step 6: Create PR

1. Push branch to remote
2. Create PR with structured description:
   - Summary (1-3 bullet points)
   - Changes made
   - Test plan
   - Screenshots (if UI changes)
3. Add labels and reviewers if configured

## Gotchas

- Always rebase onto the target branch before creating the PR — stale branches cause merge conflicts that block reviewers and CI
- `gh pr create` fails silently if the branch has not been pushed — always push with `-u` first to set the upstream tracking branch
- Use draft PRs (`--draft`) for work-in-progress — this prevents accidental review requests and signals the PR is not yet ready for feedback
- Changelog updates should go in a separate commit from code changes — mixing them makes reverts harder and pollutes the diff reviewers need to focus on
- Never force-push after PR review has started — it destroys review comments and makes it impossible for reviewers to see what changed since their last review
