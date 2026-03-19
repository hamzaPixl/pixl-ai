# Crew Delegation Rules

## When to Use the Orchestrator

Use the `orchestrator` agent when:
- The task spans multiple domains (frontend + backend + devops)
- You need to coordinate 3+ agents working in sequence or parallel
- The task maps to a multi-agent skill (`/website-project`, `/multi-agent-pipeline`)

For single-domain tasks, delegate directly to the specialist agent.

## Agent Routing Table

| Task domain | Agent | Example tasks |
|-------------|-------|---------------|
| UI/React/Next.js/CSS | `frontend-engineer` | Build components, implement designs, fix styling |
| API/Backend/Database | `backend-engineer` | Add endpoints, write migrations, fix queries |
| End-to-end features | `fullstack-engineer` | Feature crossing API boundary, form → API → DB |
| Architecture/Design | `architect` | System design, DDD modeling, service boundaries |
| Testing/QA | `qa-engineer` | Write tests, browser verification, review loops |
| Docker/CI/Deployment | `devops-engineer` | Dockerfiles, CI pipelines, cloud deployment |
| Security/Auth | `security-engineer` | OWASP audit, RBAC review, vulnerability scan |
| Task planning | `product-owner` | Sprint planning, task breakdown, acceptance criteria |
| Code review | `tech-lead` | Review PRs, enforce quality gates, technical decisions |
| Quick research | `explorer` | Find files, understand patterns, codebase questions |
| Build/type errors | `build-error-resolver` | Fix compilation failures with minimal diffs |
| Doc updates | `doc-updater` | Sync docs with code changes |
| New project onboarding | `onboarding-agent` | Scan codebase, generate CLAUDE.md, catalog stack |

## Skill-First Rules

- **Never build backend infrastructure from scratch** — the SaaS studio stack (`/saas-microservice`) has foundation packages covering identity, tenancy, RBAC, audit, outbox, and more
- **Check `/website` before building landing pages** — it has an 8-step workflow with parallel agent routing
- **Use `/ddd-pattern` for domain modeling** — don't manually create aggregates, repositories, value objects
- **Use `/self-review-fix-loop` for quality** — automated review and fix cycle before submitting
