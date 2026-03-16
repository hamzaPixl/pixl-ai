---
name: claude-md
description: "Generate or improve CLAUDE.md files. Two modes: (1) Generate — analyze a codebase and create a comprehensive CLAUDE.md from scratch, (2) Improve — audit existing CLAUDE.md files, score quality, and apply targeted updates. Use when asked to create, generate, audit, improve, fix, or maintain CLAUDE.md files."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
argument-hint: "<mode: generate|improve> [path]"
---

# CLAUDE.md Manager

Unified skill for creating and maintaining CLAUDE.md files. Replaces the separate `claude-md-generator` and `claude-md-improver` skills.

## Mode Detection

| Argument | Mode |
|---|---|
| `generate` or no existing CLAUDE.md | Generate from scratch |
| `improve` or existing CLAUDE.md found | Audit and improve |
| No argument | Auto-detect based on CLAUDE.md presence |

---

## Mode A: Generate

Create a CLAUDE.md by analyzing the codebase.

### Step 1: Scan (Parallel — 3 Agents)

Spawn 3 Explore agents to scan in parallel:
1. **Agent A**: Project structure, directories, key files, build system
2. **Agent B**: Code patterns, naming conventions, architecture
3. **Agent C**: Testing patterns, CI/CD, deployment

### Step 2: Analyze

1. Identify the project type (library, service, monorepo, CLI)
2. Map the tech stack (language, framework, build tools)
3. Extract common patterns (file naming, directory structure, imports)
4. Identify testing framework and conventions

### Step 3: Extract Conventions

1. Extract coding standards from existing code
2. Identify error handling patterns
3. Map dependency injection or configuration patterns
4. Note security practices and authentication patterns
5. Identify deployment and infrastructure patterns

### Step 4: Assemble

Generate CLAUDE.md with sections:
1. **Project Overview** — What it is, tech stack, key commands
2. **Architecture** — Directory structure, key modules, data flow
3. **Conventions** — Naming, file structure, import order, error handling
4. **Development** — How to run, test, build, deploy
5. **Patterns** — Specific patterns to follow when contributing

Check `examples/` directory for project-type-specific templates.

---

## Mode B: Improve

Audit and improve existing CLAUDE.md files.

### Phase 1: Discovery

Find all CLAUDE.md files:

```bash
find . -name "CLAUDE.md" -o -name ".claude.md" -o -name ".claude.local.md" 2>/dev/null | head -50
```

**File Types:**

| Type | Location | Purpose |
|---|---|---|
| Project root | `./CLAUDE.md` | Primary project context (shared) |
| Local overrides | `./.claude.local.md` | Personal settings (gitignored) |
| Global defaults | `~/.claude/CLAUDE.md` | User-wide defaults |
| Package-specific | `./packages/*/CLAUDE.md` | Module-level in monorepos |

### Phase 2: Quality Assessment

Score each file against criteria:

| Criterion | Weight | Check |
|---|---|---|
| Commands/workflows documented | High | Build/test/deploy commands present? |
| Architecture clarity | High | Can Claude understand the structure? |
| Non-obvious patterns | Medium | Gotchas and quirks documented? |
| Conciseness | Medium | No verbose or obvious info? |
| Currency | High | Reflects current codebase state? |
| Actionability | High | Instructions executable, not vague? |

**Grades:** A (90-100), B (70-89), C (50-69), D (30-49), F (0-29)

### Phase 3: Quality Report

**ALWAYS output the quality report BEFORE making any updates.**

```markdown
## CLAUDE.md Quality Report

### Summary
- Files found: X
- Average score: X/100
- Files needing update: X

### File-by-File Assessment
#### 1. ./CLAUDE.md (Project Root)
**Score: XX/100 (Grade: X)**
| Criterion | Score | Notes |
|-----------|-------|-------|
| ... | ... | ... |
```

### Phase 4: Targeted Updates

After report, ask user for confirmation. Then apply:
- Commands or workflows discovered during analysis
- Gotchas or non-obvious patterns found in code
- Package relationships that weren't clear
- Configuration quirks

**Avoid**: Restating obvious info, generic best practices, verbose explanations.

### Phase 5: Apply

Use Edit tool to apply changes. Preserve existing content structure.

---

## What Makes a Great CLAUDE.md

- Concise and human-readable
- Actionable commands that can be copy-pasted
- Project-specific patterns, not generic advice
- Non-obvious gotchas and warnings

**Recommended sections** (use only what's relevant):
Commands, Architecture, Key Files, Code Style, Environment, Testing, Gotchas, Workflow
