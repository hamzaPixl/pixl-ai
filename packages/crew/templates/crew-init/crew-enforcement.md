# Crew Enforcement Rules

## MANDATORY Skill Usage

Before writing ANY code in these directories, you MUST first invoke the corresponding skill:

| Directory Pattern | Required Skill | Why |
|---|---|---|
| `domain/`, `entities/`, `aggregates/` | `/ddd-pattern` | Ensures correct DDD structure |
| `routes/`, `api/`, `endpoints/` | `/pydantic-api-endpoint` or `/fastapi-service` | Ensures consistent API patterns |
| `components/`, `pages/`, `app/` | `/shadcn-ui` or `/website` | Ensures design system compliance |
| `infrastructure/`, `repositories/` | `/saas-microservice` or `/ddd-pattern` | Ensures proper infrastructure patterns |

If you write to a protected directory without invoking the skill first, the `enforce-skill-first` hook will **block** the write.

## MANDATORY Agent Delegation

For multi-file changes (3+ files), you MUST delegate to a specialist agent from the routing table in `crew-delegation.md`. Never implement across 3+ files without using an agent.

| Change Scope | Required Action |
|---|---|
| Single file, simple fix | Direct edit allowed |
| 2 files, related change | Direct edit allowed |
| 3+ files | MUST use a specialist agent |
| Cross-domain (frontend + backend) | MUST use `orchestrator` or `fullstack-engineer` |

## Skill Invocation Tracking

The pixl-crew plugin tracks skill invocations per session. At session end, the `audit-skill-usage` hook will warn if files were modified without any skill or agent being used. This is a signal to improve your workflow.
