# Project Name — SaaS + Next.js

## Overview

Full-stack SaaS application with Next.js frontend and TypeScript microservice backend.

## Stack

- **Frontend**: Next.js 15 (App Router), React 19, Tailwind CSS, shadcn/ui
- **Backend**: Fastify 5, Prisma 6, TypeScript 5
- **Database**: PostgreSQL 16 + Redis 7
- **Auth**: JWT + API key dual auth (via `@project/identity`)
- **Deployment**: Docker → Google Cloud Run

## Structure

```
apps/
├── web/                     # Next.js frontend
│   ├── src/app/             # App Router pages
│   ├── src/components/      # React components
│   └── src/lib/             # Client utilities
├── api/                     # Fastify backend
│   ├── src/api/routes/      # API routes (JWT, API key, public)
│   ├── src/domain/          # DDD entities, value objects
│   └── src/infrastructure/  # Repositories, external services
packages/
├── contracts/               # Shared Zod schemas
├── config/                  # Environment config
└── ...                      # Foundation packages
```

## Commands

```bash
make dev          # Start all services
make test         # Run all tests
make build        # Build for production
make deploy       # Deploy to Cloud Run
```

## Conventions

- **API routes**: `POST /v1/resources`, `GET /v1/resources/:id`
- **Entities**: DDD-style with `create()` factory, `validate()`, domain events
- **Tests**: Vitest for unit, Supertest for integration
- **Commits**: Conventional commits (`feat:`, `fix:`, `refactor:`)
- **Multi-tenant**: All queries scoped by `tenantId` via repository layer

## Key Patterns

- Use `@project/contracts` for shared types between frontend and backend
- Use `@project/identity` for auth middleware on routes
- Use `@project/rbac` for permission guards
- Domain events via transactional outbox pattern
- Tenant isolation at repository level (never raw Prisma queries)

## Don't

- Don't write raw SQL — use Prisma
- Don't create new foundation packages — use existing ones
- Don't skip auth middleware on API routes
- Don't use `any` — use proper types from contracts
