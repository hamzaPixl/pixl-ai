---
description: Permission wildcards and sandbox best practices
globs: .claude/settings*.json
---

# Permission Wildcards

Use wildcard permissions instead of blanket `--dangerously-skip-permissions`:

```
Bash(make *)        — all Makefile targets
Bash(npm run *)     — all npm scripts
Bash(bun run *)     — all bun scripts
Bash(git *)         — all git commands (careful: includes destructive ones)
Bash(gh *)          — all GitHub CLI commands
Bash(docker *)      — all Docker commands
Bash(npx *)         — all npx commands
```

Prefer scoped wildcards over broad ones:

- `Bash(git add:*)` + `Bash(git commit:*)` is safer than `Bash(git *)`
- `Bash(npm run test:*)` is safer than `Bash(npm *)`

Never add `Bash(rm -rf:*)` or `Bash(git push --force:*)` to auto-allow.
