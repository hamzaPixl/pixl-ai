# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SaaS Studio is a TypeScript monorepo providing production-grade foundation libraries for multi-tenant SaaS applications. It contains **foundation packages** (shared infrastructure), **microservices**, and a **demo app** that showcases all packages together.

## Build & Development Commands

Package manager is **Bun** (migrated from pnpm). Build orchestration via **Turborepo**.

```bash
bun install                          # Install all workspace dependencies
bun run build                        # Build all packages (turbo, respects dependency order)
bun run dev                          # Start all services in dev mode
bun run test                         # Run all tests (vitest via turbo)
bun run typecheck                    # Type check all packages
bun run lint                         # Lint with Biome
bun run format                       # Format with Biome
bun run clean                        # Remove dist/ and node_modules
bun run check:transactions           # Validate transaction usage patterns
```

### Targeting a specific package

```bash
# Turbo filter by package name
bun run build --filter=@saas-studio/db
bun run test --filter=@saas-studio/demo

# Or run directly in a package directory
cd demo && bun run test              # vitest run
cd demo && bun run test:watch        # vitest (watch mode)
cd demo && bun run typecheck         # tsc --noEmit
```

### Demo app database

```bash
cd demo
bun run db:generate                  # prisma generate
bun run db:push                      # prisma db push
bun run db:migrate                   # prisma migrate dev
```

## Architecture

### Monorepo Workspaces

```
foundation/*    # 17 shared infrastructure packages (@saas-studio/*)
services/*      # 4 microservices (form:3002, mail:3003, media:3001, pdf:3004)
demo            # Reference SaaS app (port 3000) using all foundation packages
tooling/*       # Build/utility scripts
```

### DDD / Onion Layering

Every service and the demo app follow strict layered architecture:

```
API Layer          → Controllers, Zod schemas, route guards
Application Layer  → Services (business logic), event handlers
Domain Layer       → Entities, value objects, domain events (PURE - no external deps)
Infrastructure     → Repositories (Prisma), jobs, notifications, realtime
```

**Layer dependency rules**: API → Application → Domain ← Infrastructure. Domain depends on nothing. Infrastructure depends only on Domain.

### Foundation Package Dependency Flow

```
contracts (Zod schemas, branded types - single source of truth)
    ↓
config, domain, logger
    ↓
identity, tenancy, events
    ↓
db, rbac, audit, outbox, jobs
    ↓
observability, realtime, api-factory, notifications
```

### Key Patterns

**Multi-tenancy**: Prisma extension (`createTenantScopeExtension`) auto-injects `WHERE tenant_id = ?` on all queries. Excluded models: Tenant, AuditLog, Outbox.

**Unit of Work + Transactional Outbox**: `unitOfWork.execute()` wraps business data + audit entry + outbox entry in a single DB transaction. `OutboxWorker` polls and publishes to NATS.

**Actor Context**: `AsyncLocalStorage` provides request-scoped tenant/user context. Access via `getTenantId()`, `getActor()`, `requireAuth()` from `@saas-studio/identity`.

**Dependency Injection**: `fastify-decorators` with `@Controller`, `@Service`, `@Inject` decorators. Repository registry for DI.

**Domain Entities**: Private constructors + static factory methods (`create()`, `fromPersistence()`). Aggregate roots collect domain events. Entities return new instances on mutation (immutable style).

**Repository Pattern**: `BaseRepository<T>` and `TenantScopedRepository<T>` from `@saas-studio/db`. Each repository implements `toDomain()` and `toPersistence()` mappers.

**RBAC**: Permissions follow `resource:action` format. Register with `crudPermissions('tasks')`, guard routes with `permissionGuard(permission('tasks', 'create'))`.

### Demo App Bootstrap (main.ts)

The demo `main.ts` initializes in order: config → API factory → observability → Prisma + tenant extension → repositories → unit of work → event bus → outbox worker → event handlers → notifications → jobs → realtime → RBAC → controllers → start server.

## Code Style

- **Formatter**: Biome - 2-space indent, 100-char line width, single quotes, trailing commas, semicolons
- **TypeScript**: Strict mode, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, target ES2022, ESM modules
- **Build**: Most packages use `tsup` (ESM output). Some use raw `tsc`. Demo uses `experimentalDecorators` + `emitDecoratorMetadata`.
- **Commits**: Conventional commits

## File Organization

One class/concern per file. Barrel exports via `index.ts`. Schema files separate from logic. Infrastructure modules split by concern (connection, initialization, operations).
