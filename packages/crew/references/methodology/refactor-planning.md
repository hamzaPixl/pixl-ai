# Refactor Planning

## Principles

- Every refactor must have a clear before/after that can be verified
- Refactor in small, individually testable steps
- Never refactor and add features in the same commit
- Keep tests green at every step

## Process

1. **Define the target** — What does the code look like after?
2. **Identify the boundary** — What's in scope vs out of scope?
3. **Plan the sequence** — Order steps to keep tests passing throughout
4. **Execute incrementally** — One step, verify, commit. Repeat.
5. **Verify the result** — Compare against the target

## Common Refactoring Patterns

### Extract (move code to a new location)
- Extract function/method
- Extract class/module
- Extract shared utility

### Inline (merge code back)
- Inline function that's only called once
- Inline constant that's only used once

### Rename (clarify intent)
- Rename variable/function/class for clarity
- Rename file to match export

### Restructure (change organization)
- Move file to better directory
- Split large file into focused modules
- Merge related files

## Safety Checklist

- [ ] Tests exist for the code being refactored
- [ ] Each step keeps tests green
- [ ] No behavior changes (inputs → outputs remain identical)
- [ ] No feature additions mixed in
- [ ] Reviewed for accidental scope creep
