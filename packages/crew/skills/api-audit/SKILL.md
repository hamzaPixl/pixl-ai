---
name: api-audit
description: "Audit API endpoints for naming consistency, response shape uniformity, validation gaps, auth holes, and REST convention compliance. Supports Fastify, Express, FastAPI, and Next.js API routes. Use when asked to audit an API, review endpoint design, check API consistency, or find auth gaps."
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "<optional: path to routes directory or specific endpoint>"
---

## Overview

API audit pipeline: discovery → endpoint inventory → naming audit → response audit → validation audit → auth audit → scorecard. Read-only analysis that produces a prioritized report.

## Required References

Before starting, read `references/backend/api-design.md` for REST conventions, naming rules, and response format standards.

## Step 1: Discovery

1. **Framework detection**:
   - `package.json` with fastify/express/hapi/koa → Node.js
   - `pyproject.toml` with fastapi/django/flask → Python
   - `app/api/` or `pages/api/` directory → Next.js API routes
2. **Route file inventory**:
   - Fastify: glob for `*.routes.ts`, `*.controller.ts`, files with `fastify.get/post/put/delete`
   - Express: files with `router.get/post/put/delete` or `app.get/post/put/delete`
   - FastAPI: files with `@router.get/post/put/delete` or `@app.get/post/put/delete`
   - Next.js: `app/api/**/route.ts` or `pages/api/**/*.ts`
3. **Auth infrastructure**:
   - Grep for auth middleware, guards, decorators (`authenticate`, `requireAuth`, `Depends`, `preHandler`)
   - Identify auth strategies (JWT, API key, session, OAuth)

## Step 2: Endpoint Inventory

For each endpoint, extract:

| Field | Source |
|-------|--------|
| Method | GET/POST/PATCH/PUT/DELETE |
| Path | Route path with parameters |
| Handler | Function name and file location |
| Auth | Required/optional/none |
| Validation | Input schema (Zod/Joi/Pydantic) or none |
| Response type | Typed response or untyped |

Build complete inventory table.

## Step 3: Naming Audit

Check each endpoint against REST conventions:

1. **Resource naming**:
   - Nouns, not verbs (`/users` not `/getUsers`)
   - Plural collection names (`/users` not `/user`)
   - Lowercase with hyphens (`/user-profiles` not `/userProfiles`)
2. **Method-path alignment**:
   - GET for reads, POST for creates, PATCH for updates, DELETE for deletes
   - No `POST /deleteUser` or `GET /createItem`
3. **Path parameter naming**:
   - Consistent ID parameter naming (`:id` vs `:userId` vs `:user_id`)
   - Nested resources use parent path (`/users/:id/posts` not `/user-posts/:userId`)
4. **Versioning**:
   - Consistent versioning strategy (path prefix `/v1/` or header)

## Step 4: Response Shape Audit

1. **Envelope consistency**:
   - All list endpoints return `{ data: [], meta: { total, limit, offset } }`
   - All single endpoints return `{ data: { ... } }`
   - All errors return `{ error: { code, message } }`
2. **Pagination**:
   - All list endpoints support pagination (limit/offset or cursor)
   - Consistent pagination parameter names
3. **Status codes**:
   - 200 for success, 201 for created, 204 for deleted
   - 400 for validation, 401 for unauth, 403 for forbidden, 404 for not found
   - No 200 with error body
4. **Response typing**:
   - All endpoints return typed responses (Zod schema, Pydantic model, or TypeScript interface)
   - No `any` or untyped responses

## Step 5: Validation Audit

1. **Input validation**:
   - All POST/PATCH endpoints validate request body
   - All endpoints with query params validate them
   - Path parameters validated (UUID format, numeric ID)
2. **Schema completeness**:
   - Required fields marked as required
   - String fields have max length
   - Numeric fields have min/max bounds
   - Enum fields use enum validation
3. **Missing validation**:
   - File uploads without size/type limits
   - Pagination without max limit
   - Search queries without sanitization

## Step 6: Auth Audit

1. **Unprotected endpoints**:
   - Endpoints that should require auth but don't
   - Compare against route patterns (CRUD on user data = needs auth)
2. **Auth consistency**:
   - Same resource has mixed auth requirements
   - Admin-only routes without role checks
3. **Tenant isolation**:
   - Multi-tenant routes filter by tenant ID
   - No cross-tenant data access possible
4. **Rate limiting**:
   - Public endpoints without rate limits
   - Auth endpoints (login) without brute-force protection

## Step 7: Scorecard

```
## API Audit Scorecard

| Category          | Score | Issues |
|-------------------|-------|--------|
| Naming            | X/10  | N      |
| Response Shape    | X/10  | N      |
| Validation        | X/10  | N      |
| Auth & Security   | X/10  | N      |
| **Overall**       | X/10  | N      |

### Critical (fix immediately)
- ...

### Warnings (fix soon)
- ...

### Suggestions (nice to have)
- ...
```
