# Agent Registry

Machine-readable index of all pixl-crew agents. Used by the orchestrator for routing validation and by developers for quick reference.

## Agent Index

| Agent | Model | Memory | Permission Mode | Trigger Keywords | Bound Skills | Delegates To |
|-------|-------|--------|-----------------|------------------|--------------|--------------|
| `orchestrator` | opus | project | default | "build", "create project", "scaffold", "coordinate", multi-phase | website-project, fullstack-app, task-plan, file-parser | explorer, architect, product-owner, frontend-engineer, backend-engineer, fullstack-engineer, tech-lead, qa-engineer, devops-engineer, security-engineer |
| `architect` | opus | project | plan (read-only) | "design", "architecture", "DDD", "bounded context", "CQRS", trade-offs | ddd-pattern, task-plan | — |
| `product-owner` | sonnet | — | default | "plan", "sprint", "decompose", "acceptance criteria", "prioritize" | task-plan, sprint-planning, content-marketing | — |
| `tech-lead` | opus | project | default | "review", "code quality", "conventions", "standards", pre-merge | self-review-fix-loop, pr-creation | — |
| `frontend-engineer` | inherit | — | default | "React", "Next.js", "component", "page", "shadcn", "website", "i18n", "Figma" | website, shadcn-ui, i18n-setup, website-theme, website-layout, design-extraction, react-doctor, seo-audit, content-marketing | — |
| `backend-engineer` | inherit | — | default | "API endpoint", "Fastify", "Prisma", "entity", "schema", "repository" | ddd-pattern | — |
| `fullstack-engineer` | inherit | — | default | "end-to-end", "API + UI", "cross-boundary", "Zod schemas" | ddd-pattern, shadcn-ui, file-parser | — |
| `qa-engineer` | sonnet | — | default | "test", "TDD", "browser verify", "self-review", "review-fix cycle" | self-review-fix-loop, agent-browser, react-doctor, code-reduction, seo-audit, test-runner, cto-review, cartographer | — |
| `devops-engineer` | sonnet | — | default | "Docker", "CI/CD", "Cloud Run", "PM2", "Makefile", "deploy" | docker-cloudrun, pm2, makefile | — |
| `security-engineer` | opus | project | plan (read-only) | "OWASP", "security audit", "RBAC", "CVE", "vulnerability", "dependency scan" | self-review-fix-loop | — |
| `explorer` | haiku | user | plan (read-only) | "find", "where is", "search", "grep", "structure overview" | — | — |
| `onboarding-agent` | haiku | user | plan (read-only) | "onboard", "new client", "new project", "generate CLAUDE.md", "scan codebase" | client-project-setup | — |
| `build-error-resolver` | sonnet | — | default | "build error", "type error", "compilation failure", "CI failing", "tsc errors" | — | — |
| `doc-updater` | haiku | user | default | "update docs", "refresh codemap", "stale documentation", "sync docs" | — | — |

## Selection Heuristic

1. **Scope check** — Does the task span multiple modules or require coordination? → `orchestrator`
2. **Domain match** — Match the primary domain (frontend, backend, security, etc.) to the specialist
3. **Read vs write** — Read-only analysis? → `architect`, `security-engineer`, or `explorer`. Implementation? → engineer agents
4. **Cost optimization** — Simple search? → `explorer` (haiku). Pattern-following? → sonnet agents. Deep reasoning? → opus agents
