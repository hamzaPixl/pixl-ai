# TDD Methodology

## Iron Law

No production code without a failing test first.

## Three-Phase Cycle

### RED — Write a Failing Test
Write ONE focused test that fails for the right reason (not a syntax error).

Ask yourself:
- What behavior am I testing?
- What input triggers it?
- What output do I expect?
- What is the simplest case?

Verify it fails before proceeding.

### GREEN — Make It Pass
Write the minimum code to make the test pass.

Rules:
- No over-engineering
- No extra features
- Ugly code is acceptable at this stage

### REFACTOR — Clean Up
With all tests passing:
- Remove duplication
- Improve naming
- Extract methods/functions

Run tests after every change. No new functionality in this phase.

### COMMIT
After each green+refactor cycle: `feat: add <specific behavior>`

## Red Flags

| Symptom | Problem | Fix |
|---------|---------|-----|
| Writing tests after code | Not TDD | Delete code, write test first |
| Test passes immediately | Not testing new behavior | Write test for actual new behavior |
| Skipping refactor | Tech debt accumulation | Refactor before next test |
| Large tests | Testing too much at once | Break into smaller tests |
| Mocking many things | Too many dependencies | Reduce coupling first |

## Cycle Output Format

```markdown
### TDD Cycle: [description]
**RED:** Test `test_name()` — Expected: [behavior] — Running... FAILED
**GREEN:** [Brief minimal change] — Running... PASSED
**REFACTOR:** [Changes or "None needed"] — Running... PASSED
**COMMIT:** `type: message`
```

## Guidelines

- One test at a time — never batch
- Each cycle should take minutes, not hours
- If stuck in RED for too long, simplify the test
- If GREEN requires large changes, the test was too ambitious
- Tests document behavior — name them accordingly
