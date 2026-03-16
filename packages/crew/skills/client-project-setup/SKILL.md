---
name: client-project-setup
description: "Onboard a new client project: scan the codebase, generate a CLAUDE.md, catalog the tech stack, and create a context packet. Use when starting work on a new project, onboarding a client, or setting up Claude for a new codebase."
allowed-tools: Read, Write, Bash, Glob, Grep, Agent
argument-hint: "<path to project directory>"
context: fork
---

## Overview

Client project onboarding pipeline: scan → catalog → generate CLAUDE.md → create context packet. Uses the onboarding-agent for exploration and produces ready-to-use project documentation.

## Required References

Before starting, read `references/methodology/client-onboarding.md` for the onboarding checklist and CLAUDE.md template.

## Step 1: Validate Input

1. Confirm the project path exists and is a valid directory
2. Check if a `CLAUDE.md` already exists (offer to audit/improve instead of overwrite)
3. Check if `.claude/` directory exists

## Step 2: Codebase Exploration

Delegate to the `onboarding-agent` to perform a read-only scan of the project:

```
Launch onboarding-agent with prompt:
"Scan the project at {path}. Produce a complete onboarding report including:
stack summary, tech stack table, directory map, key files, conventions,
CLAUDE.md draft, and risks/gaps."
```

## Step 3: Generate CLAUDE.md

Delegate to the `/claude-md` skill to produce the CLAUDE.md. Pass it the onboarding-agent's report as additional context. This avoids duplicating the CLAUDE.md generation logic.

If a `CLAUDE.md` already exists, use `/claude-md` in improve mode instead to audit and enhance it.

## Step 4: Create Context Packet

Generate a `.context/project-overview.md` file with:

1. **Stack summary** — for sharing with team members
2. **Architecture diagram** (ASCII) — high-level component relationships
3. **Dependency map** — key external services and integrations
4. **Risk register** — technical debt, missing tests, security concerns

## Step 5: Setup Recommendations

Based on the scan, recommend:

1. **Missing infrastructure**:
   - No CI/CD → suggest GitHub Actions
   - No linting → suggest ESLint/Prettier or Ruff
   - No testing → suggest test framework
   - No Docker → suggest containerization
2. **pixl-crew integration**:
   - Which agents are most relevant for this project type
   - Which skills to use first (e.g., `/seo-audit` for websites, `/ddd-pattern` for backends)
3. **Quick wins**:
   - Easy improvements that can be made immediately

## Step 6: Summary

Output a completion summary:

```
## Client Project Setup Complete

✅ CLAUDE.md generated at {path}/CLAUDE.md
✅ Context packet at {path}/.context/project-overview.md
✅ Tech stack cataloged: {framework} / {language} / {db}

### Recommended Next Steps
1. Review and customize CLAUDE.md
2. Run `/self-review-fix-loop` for initial code quality
3. {project-specific recommendation}
```
