# Patterns

## Search Before Write

- **Read before edit** — always read a file before modifying it
- **Grep before creating** — search for existing implementations before writing new ones
- **Check imports** — verify a module/function exists before importing it
- **Explore before building** — scan `skills/`, `studio/stacks/`, and `references/` for existing solutions

## Prefer Existing Patterns

- Match the style of surrounding code — don't introduce new patterns in isolation
- Use existing utility functions before creating new ones
- Follow established naming conventions in the project
- Check for shared types/interfaces before defining duplicates

## Incremental Changes

- Make one logical change at a time, verify it works, then move to the next
- Don't refactor while fixing a bug — separate concerns into separate commits
- Test after each change, not just at the end
