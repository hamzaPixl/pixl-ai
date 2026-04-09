---
name: investigate
description: "Root cause debugging with enforced investigation before fixing. 4-phase methodology: reproduce → diagnose → hypothesize → fix. Prevents jumping to solutions. Use when debugging a bug, investigating a failure, or when something broke and the cause is unclear."
allowed-tools: Read, Bash, Glob, Grep, Edit, Write, Agent
argument-hint: "<symptom or error message>"
---

## Overview

Structured debugging that enforces investigation before fixing. Inspired by the "3-strike rule" — you must understand the root cause before writing any fix. Every fix requires a regression test.

**How this differs from other skills**:
- `/runbook` — live incident response for production systems. This skill is for code-level debugging.
- `/self-review-fix-loop` — iterative review-and-fix loop for open changes. This skill starts from a symptom and traces to root cause.
- `/test-runner` — runs tests. This skill debugs WHY tests (or features) fail.

## Phase 1: Reproduce (Read-Only)

**Goal**: Confirm the bug exists and define the exact failure condition.

1. **Capture the symptom**: What exactly is failing? Error message, unexpected behavior, test failure?
2. **Reproduce reliably**: Find the minimal steps to trigger the bug
   - Run the failing test: `pytest <file>::<test> -v --tb=long` or `vitest run <file> -t "<test>"`
   - Or reproduce manually via the described steps
3. **Define the contract**: What SHOULD happen vs what DOES happen?
4. **Scope the blast radius**: Is this isolated or does it affect other areas?

Output:
```
SYMPTOM: <exact error or unexpected behavior>
REPRODUCTION: <minimal steps to trigger>
EXPECTED: <what should happen>
ACTUAL: <what does happen>
SCOPE: <isolated | cross-cutting | unknown>
```

**Do NOT write any fixes yet.** Phase 1 is strictly read-only.

## Phase 2: Diagnose (Read-Only)

**Goal**: Narrow to a single root cause. Follow the evidence, not assumptions.

### Diagnostic Ladder

Work through in order — stop when you find the root cause:

1. **Read the error**: Parse the full stack trace. What line, what function, what input?
2. **Trace the data flow**: Follow the input from entry point to failure point
   - Use Grep to find callers: `grep -r "functionName" --include="*.ts"`
   - Read each file in the call chain
3. **Check recent changes**: `git log --oneline -20 -- <affected-files>` and `git diff HEAD~5 -- <affected-files>`
4. **Compare working vs broken**: If it worked before, what changed? `git bisect` if needed
5. **Check dependencies**: Version changes, config changes, environment differences
6. **Inspect state**: Add temporary logging or use debugger to inspect runtime values

### Diagnostic Rules

- **No guessing**: Every hypothesis must be backed by evidence from code or logs
- **One variable at a time**: Don't change multiple things while debugging
- **Read before assuming**: Always read the actual code — don't assume you know what it does
- **Check the obvious first**: Typos, wrong variable names, missing imports, stale caches

Output:
```
ROOT CAUSE: <specific technical explanation>
EVIDENCE: <what code/logs/behavior proves this>
AFFECTED CODE: <file:line references>
CONFIDENCE: <high | medium | low>
```

**Do NOT write any fixes yet.** Phase 2 is strictly read-only.

## Phase 3: Hypothesize

**Goal**: Design the fix before implementing it.

1. **Propose the fix**: What specific code change will resolve the root cause?
2. **Assess risk**: Could this fix break anything else?
3. **Identify the test**: What regression test will prevent this bug from recurring?
4. **Consider alternatives**: Is there a simpler fix? A more robust fix?

If confidence from Phase 2 is "low":
- Spawn an Explore agent to search for similar patterns in the codebase
- Check if this is a known issue pattern (search error messages, check issues)
- If still uncertain, present findings to the user before proceeding

Output:
```
FIX: <specific change description>
FILES: <files to modify>
RISK: <what could break>
TEST: <regression test to write>
ALTERNATIVE: <simpler or more robust option, if any>
```

## Phase 4: Fix + Verify

**Goal**: Implement the fix with a regression test.

### 4a: Write the Regression Test First (TDD Red)

Write a test that:
- Reproduces the exact bug (fails before the fix)
- Verifies the correct behavior (passes after the fix)
- Is specific enough to catch regressions

Run the test — confirm it FAILS for the right reason.

### 4b: Apply the Fix

Make the minimum change needed to fix the root cause. Do not:
- Refactor surrounding code
- Fix unrelated issues
- Add features
- Change things "while you're in there"

### 4c: Verify

1. Run the new regression test — confirm it PASSES
2. Run related tests — confirm nothing broke: `pytest <directory> --tb=short -q` or `vitest run <directory>`
3. Re-check the original symptom — confirm it's resolved
4. If the fix doesn't work, return to Phase 2 — do NOT layer fixes on top of fixes

## Anti-Patterns

- **Shotgun debugging**: Changing random things hoping something works. Return to Phase 2.
- **Fix layering**: Adding a second fix on top of a failed first fix. Revert and start over.
- **Symptom fixing**: Suppressing the error instead of fixing the cause (try/catch around the bug, `|| true`, ignoring the return value).
- **Over-fixing**: Refactoring the entire module when one line was wrong.
- **Skipping reproduction**: "I think I know what's wrong" — always reproduce first.

## Gotchas

- Intermittent bugs need multiple reproduction attempts — don't declare "can't reproduce" after one try
- Race conditions require stress testing: run the test 10x in a loop
- Environment-dependent bugs: check Node/Python version, OS, env vars, .env files
- If `git bisect` points to a merge commit, dig into the individual commits within it
- Memory/state bugs may not manifest in test isolation — check for global state pollution
