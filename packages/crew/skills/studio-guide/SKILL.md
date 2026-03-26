---
name: studio-guide
description: "Explain how to use pixl-crew's studio stacks for project scaffolding. Covers the nextjs stack (website with i18n, blog, Stripe, Supabase), saas stack (backend microservices with 18 foundation packages), the scaffold.sh token system, and when to use each stack vs building from scratch. Use when asked 'how does studio work', 'what stacks are available', 'how to scaffold a project', 'explain studio templates', or 'how to use studio'."
allowed-tools: Read, Glob, Grep
argument-hint: "<optional: nextjs | saas | scaffold | tokens>"
disable-model-invocation: true
---

## Overview

Explains the pixl-crew **studio** system — pre-built project stacks and a scaffolding pipeline that replaces `{{TOKEN}}` placeholders to generate production-ready projects. **Never build infrastructure from scratch** when a stack provides it.

## Step 1: Identify Focus

| Argument / Question | Focus                                   |
| ------------------- | --------------------------------------- |
| `nextjs`            | Next.js website stack details           |
| `saas`              | SaaS backend microservice stack details |
| `scaffold`          | How scaffold.sh works                   |
| `tokens`            | Token reference and how to define them  |
| _(no argument)_     | Full overview of all stacks             |

## Step 2: Studio Architecture

Two stacks live under `studio/stacks/`:

- **`nextjs/`** — Full Next.js website scaffold. See `studio/stacks/nextjs/README.md` for complete docs (components, hooks, types, API routes, pages).
- **`saas/`** — Backend microservice scaffold with 18 foundation packages and a service template. See `studio/stacks/saas/` for structure.

Each stack has a `manifest.yaml` defining its token registry, conditional files, and file conditions.

## Step 3: Scaffolding Process

Three stages:

### 3a. Token file — `KEY=VALUE` pairs

```
PROJECT_NAME=Acme Corp
PROJECT_SLUG=acme-corp
PRIMARY_COLOR_HSL=217 91% 60%
FONT_SANS=Inter
```

See `studio/stacks/nextjs/manifest.yaml` for the full token registry with examples and fallbacks.

### 3b. Features file (optional) — enables conditional files

```
stripe
supabase
blog
```

### 3c. Run scaffold

```bash
make scaffold STACK=nextjs    # Interactive — prompts for each token
# or manually:
bash scripts/scaffold.sh studio/stacks/nextjs/ <target-dir> <tokens-file> [features-file]
```

This copies all files, replaces `{{TOKEN}}` in `.tmpl` files (stripping `.tmpl`), skips gated files, and expands multi-entity templates.

## Step 4: Next.js Stack (if relevant)

Key features: 10 pages, i18n (FR/NL/EN), MDX blog, shadcn/ui + premium CSS, Stripe/Supabase/Resend integrations, SEO (sitemap, OG, Schema.org), accessibility (WCAG AA), PWA manifest.

Read `studio/stacks/nextjs/README.md` for full details.

## Step 5: SaaS Stack (if relevant)

**18 foundation packages** (pre-built, shared across services):

| Package           | Purpose                                               |
| ----------------- | ----------------------------------------------------- |
| `identity`        | User authentication and identity management           |
| `tenancy`         | Multi-tenant isolation                                |
| `rbac`            | Role-based access control                             |
| `audit`           | Audit logging                                         |
| `domain`          | DDD base classes (Entity, ValueObject, AggregateRoot) |
| `contracts`       | Shared DTOs and interfaces                            |
| `events`          | Domain event infrastructure                           |
| `outbox`          | Transactional outbox pattern                          |
| `db`              | Database utilities and connection management          |
| `config`          | Configuration management                              |
| `logger`          | Structured logging                                    |
| `observability`   | Metrics and tracing                                   |
| `api-factory`     | Fastify route/plugin factory                          |
| `jobs`            | Background job processing                             |
| `notifications`   | Email/push notification service                       |
| `realtime`        | WebSocket/SSE real-time communication                 |
| `eslint-tsconfig` | Shared linting and TypeScript config                  |

Service template generates a complete DDD microservice with entity, events, repository, routes, Zod schemas, Prisma schema, and Dockerfile.

## Step 6: When to Use What

| Building                             | Use                                               |
| ------------------------------------ | ------------------------------------------------- |
| New website / landing page           | `stacks/nextjs/` via `/website` skill             |
| New backend service / API            | `stacks/saas/` via `/saas-microservice` skill     |
| New fullstack app                    | Orchestrator → `/fullstack-app` (combines both)   |
| Adding endpoints to existing service | Backend-engineer agent (follow existing patterns) |
| DDD refactoring                      | `/ddd-pattern` skill                              |

## Step 7: Related Skills

- `/website` — builds a Next.js site (uses nextjs stack)
- `/saas-microservice` — scaffolds a backend service (uses saas stack)
- `/fullstack-app` — end-to-end app (uses both stacks)
- `/website-theme`, `/website-layout` — modify existing websites
