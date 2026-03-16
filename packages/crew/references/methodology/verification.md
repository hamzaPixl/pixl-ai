# Verification Checklist

## Iron Law

Evidence before assertions. Never claim "done" without proof. Show output, don't say it passed.

## Required Checks

All items require evidence (command output, screenshots, logs).

### 1. Tests Pass
Run the full test suite and show raw output.

Not acceptable:
- "Tests should pass"
- "I ran them earlier"
- "It works on my machine"

### 2. Build Succeeds
Run the build command and show completion message.

### 3. Lint / Type Check Passes
Run linter and type checker, show clean output or explicit "no errors".

### 4. Requirements Met
- Re-read the original request
- Check each requirement is implemented
- Verify edge cases are handled

### 5. No Debug Artifacts
```bash
grep -r "console.log\|print(\|debugger\|binding.pry" src/
```
Remove any found before completing.

### 6. No TODOs Left Behind
```bash
grep -rn "TODO\|FIXME\|XXX\|HACK" <changed-files>
```
For each found: complete it, create a ticket, or document why it's acceptable.

## Verification Commands by Stack

**Python:**
```bash
pytest -v
mypy .
ruff check .
```

**Node / TypeScript:**
```bash
npm test
npx tsc --noEmit
npx eslint .
npm run build
```

**Go:**
```bash
go test ./...
go vet ./...
golangci-lint run
go build ./...
```

## Red Flags — Stop and Verify

| Thought | Action |
|---------|--------|
| "I'm pretty sure it works" | Run the tests. Show output. |
| "It worked when I tested manually" | Run automated tests. |
| "It's a small change, doesn't need testing" | All changes need testing. |
| "The tests were passing before my change" | Run them again now. |

## Completion Output

```markdown
## Verification
- **Tests:** PASS (X passed, 0 failed)
- **Build:** PASS
- **Lint:** PASS (0 errors, 0 warnings)
- **Type Check:** PASS
- **Requirements:** [checklist of each requirement with status]
- **Clean Code:** No debug artifacts, no unresolved TODOs
- **Status:** COMPLETE
```

## Partial Completion

If any check fails:
```markdown
## Verification
- **Status:** BLOCKED
- **Completed:** [what passed]
- **Blocked:** [what failed with output]
- **Next Steps:** [specific actions to unblock]
```
