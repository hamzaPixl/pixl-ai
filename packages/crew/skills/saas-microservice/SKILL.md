---
name: saas-microservice
description: "Build a TYPESCRIPT SaaS microservice with DDD, using the studio/stacks/saas foundation (identity, RBAC, tenancy, audit, outbox). Orchestrates domain modeling, API implementation, testing, security review, and deployment. Routing: for a PYTHON API → /fastapi-api (standalone) or /fastapi-service (monorepo)."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
argument-hint: "<service name, primary entity, and domain description>"
context: fork
disable-model-invocation: true
---

## Overview

Orchestrates building a complete SaaS microservice using the studio's saas stack. Scaffolds from the foundation packages and service template, then implements domain logic, API endpoints, tests, and deployment.

## Studio Stack

Scaffold from: `studio/stacks/saas/` (17 foundation packages + service template)

## Suggested Team

- **architect** — Domain modeling, bounded context mapping, aggregate design
- **backend-engineer** — Entity implementation, routes, repositories
- **qa-engineer** — Test writing, review loops
- **devops-engineer** — Docker, CI/CD, Cloud Run deployment
- **security-engineer** — RBAC review, security audit

## Process

### Phase 1: Domain Design

1. Run `/ddd-pattern` Discovery phase — analyze the domain
2. Run `/ddd-pattern` Model phase — entities, aggregates, value objects
3. Delegate to **architect** for bounded context review

### Phase 2: Scaffold

4. Copy `studio/stacks/saas/foundation/` packages (use pruning rules for minimal set)
   - **Important**: Use `rsync -a --exclude node_modules` instead of `cp -r` to avoid broken symlinks from `node_modules/.bin`
5. Apply `studio/stacks/saas/service-template/` with token replacement:
   - `SERVICE_NAME`, `SERVICE_NAME_PASCAL`, `SERVICE_PORT`
   - `ENTITY_NAME`, `ENTITY_SLUG`, `ENTITY_PLURAL`, `ENTITY_PLURAL_SLUG`
   - `FOUNDATION_DEPS` — the **full** JSON dependencies block for `package.json` (includes `@prisma/client`, needed `@saas-studio/*` packages, and `zod`). Use the pruning rules in `manifest.yaml` to include only required foundation packages.
   - `ENTITIES` (optional) — comma-separated list of additional entities to scaffold, e.g. `Article,Category:Categories,Tag`. Supports `Name:Plural` syntax for irregular plurals. The first entity uses the primary `ENTITY_*` tokens above.
6. **Post-scaffold**: After running `scaffold.sh`, write `package.json` directly if the `FOUNDATION_DEPS` token needs multi-line content (the tokens file is line-based, so complex JSON should be written as a post-processing step).
7. Run `bun install` and verify clean build

### Phase 3: Implement

8. Implement domain entity (private ctor, static factories, immutable mutations)
9. Implement Prisma repository (upsert-based save, toDomain/toPersistence)
10. Implement Fastify routes (CRUD with permission guards, Zod validation)
11. Write Zod schemas for request/response validation
12. Bootstrap service entry point (PrismaClient → RBAC → apiFactory → routes → start)

### Phase 4: Quality & Deploy

13. Write tests (domain unit tests, API integration tests)

14. **Parallel Quality Wave** — You MUST spawn the following 3 agents in parallel via the `Task` tool. Do NOT run these sequentially.

| Agent | Role              | Responsibility                                                                                                                                                                                                                               |
| ----- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A     | qa-engineer       | Run `/self-review-fix-loop` — correctness, coverage, maintainability. **File ownership:** test files (`__tests__/`, `*.test.ts`, `*.spec.ts`) and source files flagged by the review loop. DO NOT modify deployment or infrastructure files. |
| B     | security-engineer | RBAC audit, JWT handling, input validation, injection surface review. **File ownership:** `src/routes/`, `src/middleware/`, permission guard files, Zod schemas. DO NOT modify test files or deployment files.                               |
| C     | devops-engineer   | Run `/docker-cloudrun` — containerize, deploy, verify health checks. **File ownership:** `Dockerfile`, `docker-compose*.yml`, `.github/workflows/`, `cloudbuild.yaml`, deployment configs. DO NOT modify source code or test files.          |

Each agent prompt MUST include:

- The service directory path and service name
- Explicit file ownership guard: "You MUST NOT create or modify any files outside your assigned ownership list above"
- Context from Phase 3 (entity name, route paths, schema locations)

After all 3 agents complete:

15. **Coordinator Verification** — Run all checks to confirm no conflicts:
    - `bun run build`
    - `bun run test`
    - `bun run typecheck`
    - `bun run check:transactions`

## Reference Docs

See `reference.md` for saas-studio architectural documentation:

- ARCHITECTURE.md — System architecture and patterns
- FOUNDATION.md — Foundation package catalog and usage
- SERVICES.md — Service implementation guide
- API.md — API design conventions
- DEPLOYMENT.md — Deployment guide
