# API Reference

This document provides the complete API reference for SaaS Studio services.

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

### Token Structure

```json
{
  "sub": "user-id",
  "tenantId": "tenant-id",
  "email": "user@example.com",
  "roles": ["admin"],
  "permissions": ["items:create", "items:read"],
  "iat": 1705312200,
  "exp": 1705315800
}
```

## Headers

### Required Headers

| Header          | Description          | Example            |
| --------------- | -------------------- | ------------------ |
| `Authorization` | JWT Bearer token     | `Bearer eyJhbG...` |
| `Content-Type`  | Request content type | `application/json` |

### Optional Headers

| Header             | Description                     | Example      |
| ------------------ | ------------------------------- | ------------ |
| `X-Tenant-ID`      | Override tenant (if not in JWT) | `tenant-123` |
| `X-Correlation-ID` | Request correlation ID          | `req-456`    |
| `X-Request-ID`     | Unique request identifier       | `abc-789`    |

## Response Format

### Success Response

```json
{
  "data": {
    "id": "...",
    "...": "..."
  }
}
```

### List Response

```json
{
  "data": [
    { "id": "...", "...": "..." },
    { "id": "...", "...": "..." }
  ],
  "pagination": {
    "total": 100,
    "limit": 10,
    "offset": 0,
    "hasMore": true
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": [],
    "correlationId": "req-123"
  }
}
```

## Error Codes

| Code                    | HTTP Status | Description                       |
| ----------------------- | ----------- | --------------------------------- |
| `BAD_REQUEST`           | 400         | Invalid request format            |
| `UNAUTHORIZED`          | 401         | Missing or invalid authentication |
| `FORBIDDEN`             | 403         | Insufficient permissions          |
| `NOT_FOUND`             | 404         | Resource not found                |
| `CONFLICT`              | 409         | Resource already exists           |
| `UNPROCESSABLE_ENTITY`  | 422         | Validation error                  |
| `INTERNAL_SERVER_ERROR` | 500         | Server error                      |

---

## Health Endpoints

All services expose health check endpoints:

### Liveness Probe

```
GET /health
```

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Readiness Probe

```
GET /ready
```

**Response:**

```json
{
  "status": "ok",
  "checks": {
    "database": { "status": "ok" }
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## Common Query Parameters

### Pagination

| Parameter | Type    | Default | Description            |
| --------- | ------- | ------- | ---------------------- |
| `limit`   | integer | 100     | Items per page (1-100) |
| `offset`  | integer | 0       | Skip items             |

### Filtering

| Parameter | Type   | Description      |
| --------- | ------ | ---------------- |
| `status`  | string | Filter by status |

---

## Media Service API

**Base URL:** `http://localhost:3001`

### List Media Files

```
GET /media
```

**Query Parameters:**

| Parameter | Type    | Description      |
| --------- | ------- | ---------------- |
| `status`  | string  | Filter by status |
| `limit`   | integer | Items per page   |
| `offset`  | integer | Skip items       |

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "550e8400-...",
      "tenantId": "tenant-123",
      "name": "photo.jpg",
      "originalName": "IMG_1234.jpg",
      "mimeType": "image/jpeg",
      "size": "1024000",
      "path": "uploads/photo.jpg",
      "bucket": "media",
      "url": "https://cdn.example.com/photo.jpg",
      "thumbnailUrl": "https://cdn.example.com/photo-thumb.jpg",
      "status": "ready",
      "version": 1,
      "createdAt": "2024-01-15T10:30:00.000Z",
      "updatedAt": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

### Get Media File

```
GET /media/:id
```

**Response:** `200 OK`

### Create Media File

```
POST /media
```

**Request Body:**

```json
{
  "name": "photo.jpg",
  "originalName": "IMG_1234.jpg",
  "mimeType": "image/jpeg",
  "size": 1024000,
  "path": "uploads/photo.jpg",
  "bucket": "media"
}
```

**Response:** `201 Created`

### Update Media File

```
PATCH /media/:id
```

**Request Body:**

```json
{
  "name": "renamed-photo.jpg",
  "metadata": { "tags": ["profile"] }
}
```

**Response:** `200 OK`

### Delete Media File

```
DELETE /media/:id
```

**Response:** `204 No Content`

---

## Form Service API

**Base URL:** `http://localhost:3002`

### List Forms

```
GET /forms
```

**Query Parameters:**

| Parameter | Type   | Description                      |
| --------- | ------ | -------------------------------- |
| `status`  | string | `draft`, `published`, `archived` |

### Get Form

```
GET /forms/:id
```

### Create Form

```
POST /forms
```

**Request Body:**

```json
{
  "name": "Contact Form",
  "description": "Contact us form",
  "schema": {
    "fields": [
      {
        "id": "name",
        "name": "name",
        "label": "Your Name",
        "type": "text",
        "required": true,
        "validation": {
          "minLength": 2,
          "maxLength": 100
        }
      },
      {
        "id": "email",
        "name": "email",
        "label": "Email",
        "type": "email",
        "required": true
      }
    ]
  },
  "settings": {
    "submitButtonText": "Submit",
    "successMessage": "Thank you!"
  }
}
```

### Update Form

```
PATCH /forms/:id
```

### Publish Form

```
POST /forms/:id/publish
```

**Response:** `200 OK`

### Delete Form

```
DELETE /forms/:id
```

### Submit Form

```
POST /forms/:id/submit
```

**Request Body:**

```json
{
  "data": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "metadata": {
    "source": "website"
  }
}
```

**Response:** `201 Created`

### List Form Submissions

```
GET /forms/:id/submissions
```

---

## Mail Service API

**Base URL:** `http://localhost:3003`

### List Email Templates

```
GET /mail/templates
```

**Query Parameters:**

| Parameter  | Type   | Description                      |
| ---------- | ------ | -------------------------------- |
| `category` | string | Filter by category               |
| `status`   | string | `active`, `inactive`, `archived` |

### Get Email Template

```
GET /mail/templates/:id
```

### Create Email Template

```
POST /mail/templates
```

**Request Body:**

```json
{
  "name": "welcome",
  "subject": "Welcome, {{name}}!",
  "htmlBody": "<h1>Welcome, {{name}}!</h1><p>Thank you for joining.</p>",
  "textBody": "Welcome, {{name}}! Thank you for joining.",
  "variables": [{ "name": "name", "required": true }],
  "category": "onboarding"
}
```

### Update Email Template

```
PATCH /mail/templates/:id
```

### Delete Email Template

```
DELETE /mail/templates/:id
```

### List Emails

```
GET /mail/emails
```

**Query Parameters:**

| Parameter | Type   | Description                                                 |
| --------- | ------ | ----------------------------------------------------------- |
| `status`  | string | `pending`, `queued`, `sending`, `sent`, `failed`, `bounced` |

### Get Email

```
GET /mail/emails/:id
```

### Send Email

```
POST /mail/send
```

**Request Body (with template):**

```json
{
  "templateId": "template-123",
  "fromAddress": "noreply@example.com",
  "fromName": "Example App",
  "toAddresses": ["user@example.com"],
  "data": {
    "name": "John"
  },
  "priority": 1,
  "scheduledFor": "2024-01-16T09:00:00.000Z"
}
```

**Request Body (without template):**

```json
{
  "fromAddress": "noreply@example.com",
  "toAddresses": ["user@example.com"],
  "subject": "Hello!",
  "htmlBody": "<p>Hello, World!</p>",
  "textBody": "Hello, World!"
}
```

---

## PDF Service API

**Base URL:** `http://localhost:3004`

### List PDF Templates

```
GET /pdf/templates
```

### Get PDF Template

```
GET /pdf/templates/:id
```

### Create PDF Template

```
POST /pdf/templates
```

**Request Body:**

```json
{
  "name": "invoice",
  "description": "Invoice template",
  "htmlContent": "<h1>Invoice #{{number}}</h1><p>Amount: {{amount}}</p>",
  "cssStyles": "h1 { color: #333; }",
  "variables": [
    { "name": "number", "required": true },
    { "name": "amount", "required": true }
  ],
  "pageSize": "A4",
  "orientation": "portrait",
  "margins": {
    "top": "20mm",
    "right": "15mm",
    "bottom": "20mm",
    "left": "15mm"
  },
  "footer": "<div>Page {{page}} of {{pages}}</div>"
}
```

### Update PDF Template

```
PATCH /pdf/templates/:id
```

### Delete PDF Template

```
DELETE /pdf/templates/:id
```

### List PDF Documents

```
GET /pdf/documents
```

**Query Parameters:**

| Parameter    | Type   | Description                                           |
| ------------ | ------ | ----------------------------------------------------- |
| `templateId` | string | Filter by template                                    |
| `status`     | string | `pending`, `generating`, `ready`, `failed`, `expired` |

### Get PDF Document

```
GET /pdf/documents/:id
```

### Generate PDF

```
POST /pdf/generate
```

**Request Body:**

```json
{
  "templateId": "template-123",
  "name": "Invoice-001.pdf",
  "data": {
    "number": "INV-001",
    "amount": "$500.00"
  },
  "expiresAt": "2024-02-15T00:00:00.000Z"
}
```

**Response:** `202 Accepted`

```json
{
  "data": {
    "id": "doc-123",
    "name": "Invoice-001.pdf",
    "status": "pending",
    "createdAt": "2024-01-15T10:30:00.000Z"
  }
}
```

### Delete PDF Document

```
DELETE /pdf/documents/:id
```

---

## Swagger Documentation

Each service exposes Swagger UI at `/docs`:

- Media Service: http://localhost:3001/docs
- Form Service: http://localhost:3002/docs
- Mail Service: http://localhost:3003/docs
- PDF Service: http://localhost:3004/docs

# Architecture Guide

## Overview

SaaS Studio follows Domain-Driven Design (DDD) principles with an Onion/Clean Architecture approach. This document describes the key architectural decisions and patterns used throughout the codebase.

## Layered Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        API Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │    Routes    │  │   Schemas    │  │   Middleware     │    │
│  │  (Fastify)   │  │    (Zod)     │  │  (Auth, CORS)    │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
├──────────────────────────────────────────────────────────────┤
│                    Application Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │   Commands   │  │   Queries    │  │    Handlers      │    │
│  │   (Write)    │  │   (Read)     │  │   (Use Cases)    │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
├──────────────────────────────────────────────────────────────┤
│                      Domain Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │   Entities   │  │Value Objects │  │  Domain Events   │    │
│  │ (Item, Form) │  │(Email, Money)│  │ (ItemCreated)    │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
├──────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ Repositories │  │    Prisma    │  │ External APIs    │    │
│  │ (Data Access)│  │   (ORM)      │  │ (SMTP, Storage)  │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Layer Rules

| Layer          | Can Depend On       | Cannot Depend On               |
| -------------- | ------------------- | ------------------------------ |
| API            | Application, Domain | Infrastructure (directly)      |
| Application    | Domain              | Infrastructure (directly)      |
| Domain         | Nothing (pure)      | Prisma, Fastify, external libs |
| Infrastructure | Domain              | API, Application               |

## Dependency Injection

We use a simple factory-based approach rather than heavy DI containers:

```typescript
// main.ts - Service bootstrap
async function bootstrap() {
  const prisma = new PrismaClient();

  // Create dependencies
  const itemRepository = new PrismaItemRepository(prisma);
  const unitOfWork = createUnitOfWork(prisma);

  // Create API factory
  const { app, start } = await createApiFactory({ ... });

  // Register routes with dependencies
  registerItemRoutes(app, { itemRepository, unitOfWork });

  await start();
}
```

## Multi-Tenancy

### Tenant Resolution

Tenants are resolved from incoming requests via configurable resolvers:

```typescript
// Header-based (X-Tenant-ID)
const resolver = new HeaderTenantResolver("X-Tenant-ID");

// Subdomain-based (tenant.example.com)
const resolver = new SubdomainTenantResolver("example.com");

// JWT claim
const resolver = new JwtTenantResolver();

// Composite (try multiple)
const resolver = new CompositeTenantResolver([
  new HeaderTenantResolver(),
  new JwtTenantResolver(),
]);
```

### Automatic Scoping

All Prisma queries are automatically scoped to the current tenant:

```typescript
// Prisma extension wraps all operations
const prisma = new PrismaClient().$extends(
  createTenantScopeExtension({
    excludedModels: ["Tenant", "AuditLog", "Outbox"],
  }),
);

// All queries automatically include: WHERE tenant_id = ?
const items = await prisma.item.findMany(); // Scoped to current tenant
```

### Database Schema

Every table (except system tables) includes `tenant_id`:

```sql
CREATE TABLE items (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  name VARCHAR(255) NOT NULL,
  -- ...
  INDEX idx_items_tenant_id (tenant_id)
);
```

## Actor Context

Request context is stored in AsyncLocalStorage for global access:

```typescript
// identity/src/actor/context.ts
const contextStorage = new AsyncLocalStorage<RequestContext>();

// Access anywhere in the request lifecycle
export function getTenantId(): string {
  return contextStorage.getStore()?.tenantId;
}

export function getActor(): Actor | undefined {
  return contextStorage.getStore()?.actor;
}
```

### Actor Types

```typescript
type ActorType = "user" | "system" | "service" | "anonymous";

interface Actor {
  type: ActorType;
  id?: string;
  tenantId: string;
  roles: string[];
  permissions: string[];
}
```

## Event Publishing

### Transactional Outbox Pattern

Events are published reliably using the outbox pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                     Database Transaction                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  1. Update business data (items, forms, etc.)       │    │
│  │  2. Insert audit log entry                          │    │
│  │  3. Insert outbox entry (pending event)             │    │
│  └─────────────────────────────────────────────────────┘    │
│                         COMMIT                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Outbox Worker                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  1. Poll for pending outbox entries                 │    │
│  │  2. Publish to NATS                                 │    │
│  │  3. Mark as published                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Unit of Work

```typescript
const result = await unitOfWork.execute(async (tx) => {
  // 1. Business logic
  const item = Item.create({ name: "New Item", tenantId });
  const saved = await itemRepository.save(item, tx);

  return {
    result: saved,
    // 2. Audit entry (written in same transaction)
    auditEntries: [
      {
        action: "CREATE",
        aggregateType: "Item",
        aggregateId: saved.id,
        after: saved.toPersistence(),
      },
    ],
    // 3. Outbox entry (written in same transaction)
    outboxEntries: [
      {
        eventType: "item.created",
        aggregateType: "Item",
        aggregateId: saved.id,
        payload: saved.toPersistence(),
      },
    ],
  };
});
```

## RBAC (Role-Based Access Control)

### Permission Model

Permissions follow the format: `resource:action`

```typescript
// Built-in CRUD permissions
const permissions = crudPermissions("items");
// ['items:create', 'items:read', 'items:update', 'items:delete', 'items:list']

// Custom permissions
permissionRegistry.register("items:publish");
permissionRegistry.register("items:archive");
```

### Role Hierarchy

```typescript
roleRegistry.register({
  name: "admin",
  permissions: crudPermissions("items"),
});

roleRegistry.register({
  name: "editor",
  permissions: ["items:read", "items:update", "items:list"],
  inherits: ["viewer"],
});

roleRegistry.register({
  name: "viewer",
  permissions: ["items:read", "items:list"],
});
```

### Route Guards

```typescript
fastify.post(
  "/items",
  {
    preHandler: [permissionGuard(permission("items", "create"))],
  },
  async (request, reply) => {
    // Only accessible with items:create permission
  },
);
```

## Observability

### Tracing

OpenTelemetry spans are created automatically for:

- HTTP requests
- Database queries
- Background jobs
- Custom operations

```typescript
// Automatic span for HTTP
GET /api/items → span: HTTP GET /api/items

// Automatic span for Prisma
prisma.item.findMany() → span: prisma:item:findMany

// Manual span
await withSpan('process-document', async () => {
  // Custom logic
});
```

### Metrics

Pre-configured metrics include:

- `http_request_duration_seconds` - Request latency histogram
- `http_requests_total` - Request counter by method/status
- `http_active_requests` - Gauge of active requests
- `db_query_duration_seconds` - Database query latency

### Logging

Structured JSON logging with automatic context:

```json
{
  "level": "info",
  "time": "2024-01-15T10:30:00.000Z",
  "msg": "Request completed",
  "tenantId": "tenant-123",
  "correlationId": "req-456",
  "method": "GET",
  "path": "/api/items",
  "statusCode": 200,
  "duration": 45
}
```

## Error Handling

### Domain Errors

```typescript
// contracts/src/errors/domain-errors.ts
export class NotFoundError extends DomainError {
  constructor(resource: string, id: string) {
    super(`${resource} with id ${id} not found`, "NOT_FOUND");
  }
}

export class ValidationError extends DomainError {
  constructor(message: string, details: ValidationDetail[]) {
    super(message, "VALIDATION_ERROR");
    this.details = details;
  }
}
```

### API Error Responses

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Item with id abc-123 not found",
    "correlationId": "req-456"
  }
}
```

## Testing Strategy

### Unit Tests

- Domain entities (pure logic, no dependencies)
- Value objects
- Application handlers (mocked repositories)

### Integration Tests

- Repository implementations (real database)
- API routes (Fastify inject)
- Event publishing (test containers)

### Architecture Tests

```bash
# Validate layer dependencies
pnpm lint:architecture
```

## Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Load Balancer                          │
└─────────────────────────────┬────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ API Instance │     │ API Instance │     │ API Instance │
│   (Fastify)  │     │   (Fastify)  │     │   (Fastify)  │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │    Redis     │   │     NATS     │
│  (Primary)   │   │   (Queue)    │   │  (Events)    │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Configuration Management

### Environment-Based

```typescript
// config/src/loader.ts
const config = loadConfig(ServiceConfigSchema, {
  serviceName: "item-service",
  version: "1.0.0",
});

// Validates and parses environment variables
// Throws helpful errors on missing/invalid values
```

### Schema-Driven

```typescript
const ServiceConfigSchema = BaseConfigSchema.extend({
  database: DatabaseConfigSchema,
  redis: RedisConfigSchema,
  jwt: JwtConfigSchema,
  featureFlags: z.object({
    enableBetaFeatures: z.boolean().default(false),
  }),
});
```

# Deployment Guide

This guide covers deploying SaaS Studio services in production.

## Prerequisites

- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- NATS 2.9+ (optional, for event bus)
- Docker (optional)

## Environment Configuration

### Required Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Authentication
JWT_SECRET=your-super-secret-key-min-32-chars
JWT_EXPIRES_IN=1h
JWT_REFRESH_EXPIRES_IN=7d

# Logging
LOG_LEVEL=info
NODE_ENV=production
```

### Optional Environment Variables

```env
# Redis (for jobs/caching)
REDIS_URL=redis://localhost:6379

# NATS (for events)
NATS_URL=nats://localhost:4222

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=saas-studio

# CORS
CORS_ORIGINS=https://app.example.com,https://admin.example.com

# Rate Limiting
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW=1m
```

## Build for Production

```bash
# Install dependencies
pnpm install --frozen-lockfile

# Build all packages
pnpm build

# Run type checks
pnpm typecheck

# Run tests
pnpm test
```

## Database Setup

### Generate Prisma Client

```bash
# For each service
cd services/media && pnpm db:generate
cd services/form && pnpm db:generate
cd services/mail && pnpm db:generate
cd services/pdf && pnpm db:generate
```

### Run Migrations

```bash
# For each service
cd services/media && pnpm db:migrate
cd services/form && pnpm db:migrate
cd services/mail && pnpm db:migrate
cd services/pdf && pnpm db:migrate
```

## Docker Deployment

### Dockerfile (per service)

```dockerfile
FROM node:20-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

FROM base AS build
WORKDIR /app
COPY pnpm-lock.yaml ./
COPY pnpm-workspace.yaml ./
COPY package.json ./
COPY turbo.json ./
COPY tsconfig.base.json ./
COPY foundation ./foundation
COPY services/media ./services/media

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
RUN pnpm turbo build --filter=@saas-studio/media-service

FROM base AS production
WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/services/media/dist ./dist
COPY --from=build /app/services/media/package.json ./package.json

USER node
EXPOSE 3001
CMD ["node", "dist/main.js"]
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: saas
      POSTGRES_PASSWORD: password
      POSTGRES_DB: saas_studio
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  nats:
    image: nats:2.9-alpine
    ports:
      - "4222:4222"
      - "8222:8222"

  media-service:
    build:
      context: .
      dockerfile: services/media/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3001:3001"
    depends_on:
      - postgres
      - redis
      - nats

  form-service:
    build:
      context: .
      dockerfile: services/form/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3002:3002"
    depends_on:
      - postgres
      - redis
      - nats

  mail-service:
    build:
      context: .
      dockerfile: services/mail/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3003:3003"
    depends_on:
      - postgres
      - redis
      - nats

  pdf-service:
    build:
      context: .
      dockerfile: services/pdf/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3004:3004"
    depends_on:
      - postgres
      - redis
      - nats

volumes:
  postgres_data:
```

## Kubernetes Deployment

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: media-service
  labels:
    app: media-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: media-service
  template:
    metadata:
      labels:
        app: media-service
    spec:
      containers:
        - name: media-service
          image: your-registry/media-service:latest
          ports:
            - containerPort: 3001
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: saas-secrets
                  key: database-url
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: saas-secrets
                  key: jwt-secret
          livenessProbe:
            httpGet:
              path: /health
              port: 3001
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 3001
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            limits:
              cpu: "500m"
              memory: "512Mi"
            requests:
              cpu: "100m"
              memory: "128Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: media-service
spec:
  selector:
    app: media-service
  ports:
    - port: 80
      targetPort: 3001
  type: ClusterIP
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: saas-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /media
            pathType: Prefix
            backend:
              service:
                name: media-service
                port:
                  number: 80
          - path: /forms
            pathType: Prefix
            backend:
              service:
                name: form-service
                port:
                  number: 80
          - path: /mail
            pathType: Prefix
            backend:
              service:
                name: mail-service
                port:
                  number: 80
          - path: /pdf
            pathType: Prefix
            backend:
              service:
                name: pdf-service
                port:
                  number: 80
```

## Monitoring

### Health Checks

All services expose:

- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe

### OpenTelemetry

Configure OTEL exporter to send traces to your observability platform:

```env
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector.example.com:4318
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer your-token
OTEL_SERVICE_NAME=media-service
OTEL_RESOURCE_ATTRIBUTES=environment=production,version=1.0.0
```

### Logging

Logs are output in JSON format to stdout:

```json
{
  "level": "info",
  "time": "2024-01-15T10:30:00.000Z",
  "msg": "Request completed",
  "service": "media-service",
  "tenantId": "tenant-123",
  "correlationId": "req-456",
  "method": "GET",
  "path": "/media",
  "statusCode": 200,
  "duration": 45
}
```

## Scaling

### Horizontal Scaling

Services are stateless and can be horizontally scaled:

```bash
# Docker Compose
docker-compose up --scale media-service=3

# Kubernetes
kubectl scale deployment media-service --replicas=5
```

### Database Connection Pooling

Configure connection pooling for high-traffic scenarios:

```env
DATABASE_URL=postgresql://user:pass@host:5432/db?connection_limit=20&pool_timeout=10
```

### Redis Cluster

For high availability, use Redis Cluster:

```env
REDIS_URL=redis://node1:6379,node2:6379,node3:6379
```

## Security Checklist

- [ ] Use strong JWT secret (min 32 characters)
- [ ] Enable HTTPS/TLS in production
- [ ] Configure CORS with specific origins
- [ ] Set rate limiting
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Enable database connection encryption
- [ ] Configure network policies (Kubernetes)
- [ ] Regular security updates

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump -h host -U user -d database > backup.sql

# Restore
psql -h host -U user -d database < backup.sql
```

### Disaster Recovery

1. Maintain database replicas
2. Regular automated backups
3. Test restore procedures
4. Document recovery steps

# Foundation Packages

This document provides detailed documentation for each foundation package in SaaS Studio.

## Package Dependency Graph

```
                    contracts
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
       config        domain         logger
         │              │              │
         └──────────────┼──────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
      identity       tenancy         events
         │              │              │
         └──────────────┼──────────────┘
                        │
    ┌───────────────────┼───────────────────┐
    │         │         │         │         │
    ▼         ▼         ▼         ▼         ▼
   db       rbac      audit    outbox     jobs
    │         │         │         │         │
    └─────────┼─────────┼─────────┼─────────┘
              │         │         │
              ▼         ▼         ▼
        observability realtime api-factory
```

---

## @saas-studio/contracts

**Purpose**: Zod schemas as the single source of truth for all types.

### Key Exports

```typescript
// Primitive types
import {
  UuidSchema,
  EmailSchema,
  TimestampSchema,
} from "@saas-studio/contracts";

// Branded types (type-safe IDs)
import {
  TenantIdSchema,
  CorrelationIdSchema,
  type TenantId,
} from "@saas-studio/contracts";

// Base schemas
import {
  TenantScopedSchema,
  TimestampedSchema,
  BaseEntitySchema,
} from "@saas-studio/contracts";

// Event envelope
import {
  EventEnvelopeSchema,
  EventMetadataSchema,
} from "@saas-studio/contracts";

// Pagination
import {
  PaginationParamsSchema,
  PaginatedResponseSchema,
} from "@saas-studio/contracts";

// Errors
import {
  DomainError,
  NotFoundError,
  ValidationError,
  ConflictError,
  AuthenticationError,
  AuthorizationError,
  createApiError,
  HTTP_STATUS_MAP,
} from "@saas-studio/contracts";
```

### Usage

```typescript
// Validate input
const id = UuidSchema.parse(input.id);

// Create typed IDs
const tenantId = TenantIdSchema.parse("550e8400-e29b-41d4-a716-446655440000");

// Pagination
const params = PaginationParamsSchema.parse({ limit: 10, offset: 0 });
```

---

## @saas-studio/config

**Purpose**: Type-safe environment configuration with Zod validation.

### Key Exports

```typescript
import {
  // Schema building blocks
  BaseConfigSchema,
  DatabaseConfigSchema,
  RedisConfigSchema,
  NatsConfigSchema,
  JwtConfigSchema,
  CorsConfigSchema,
  RateLimitConfigSchema,
  OtelConfigSchema,

  // Loaders
  loadConfig,
  createConfigLoader,
  requireEnv,
  getEnv,

  // Environment helpers
  isProduction,
  isDevelopment,
  isTest,
} from "@saas-studio/config";
```

### Usage

```typescript
// Define service config schema
const MyServiceConfigSchema = BaseConfigSchema.extend({
  database: DatabaseConfigSchema,
  redis: RedisConfigSchema,
  customOption: z.string().optional(),
});

// Load and validate
const config = loadConfig(MyServiceConfigSchema, {
  serviceName: "my-service",
  version: "1.0.0",
});

// Access typed config
console.log(config.database.url);
console.log(config.redis.host);
```

---

## @saas-studio/logger

**Purpose**: Structured logging with Pino, including correlation context.

### Key Exports

```typescript
import {
  Logger,
  ILogger,
  createLogger,
  createRequestLogger,
  logError,
  createNoopLogger,
} from "@saas-studio/logger";
```

### Usage

```typescript
// Create logger
const logger = createLogger({
  serviceName: "my-service",
  serviceVersion: "1.0.0",
  level: "info",
  pretty: process.env.NODE_ENV !== "production",
});

// Log with context
logger.info("User created", { userId: "123", email: "user@example.com" });
logger.error("Operation failed", { error, tenantId });

// Create child logger for request
const reqLogger = createRequestLogger(logger, {
  correlationId: "req-123",
  tenantId: "tenant-456",
});
```

---

## @saas-studio/domain

**Purpose**: DDD primitives for building domain models.

### Key Exports

```typescript
import {
  // Base classes
  Entity,
  TenantEntity,
  AggregateRoot,
  TenantAggregateRoot,
  ValueObject,

  // Value objects
  Money,
  Address,
  Email,

  // Events
  BaseDomainEvent,
  InMemoryDomainEventDispatcher,

  // Repository interfaces
  IRepository,
  ITenantRepository,
  IUnitOfWork,

  // Specification pattern
  Specification,
  ISpecification,

  // Pagination
  PaginationOptions,
  PaginatedResult,
} from "@saas-studio/domain";
```

### Usage

```typescript
// Define an entity
class Item extends TenantEntity<ItemProps> {
  get name(): string {
    return this.props.name;
  }

  static create(input: CreateItemInput): Item {
    return new Item({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      name: input.name,
      createdAt: new Date(),
      updatedAt: new Date(),
    });
  }
}

// Define a value object
class Price extends ValueObject<{ amount: number; currency: string }> {
  get amount(): number {
    return this.props.amount;
  }

  get currency(): string {
    return this.props.currency;
  }
}
```

---

## @saas-studio/identity

**Purpose**: Authentication, JWT handling, and actor context management.

### Key Exports

```typescript
import {
  // Context management
  runWithContext,
  getContext,
  requireContext,
  getActor,
  requireActor,
  getTenantId,
  requireTenantId,
  getUserId,
  requireUserId,
  getCorrelationId,

  // Actor factories
  createSystemActor,
  createServiceActor,
  createAnonymousActor,

  // Role/permission checks
  hasRole,
  hasPermission,

  // JWT operations
  signTokenPair,
  verifyToken,
  decodeToken,
  extractPayloadFromRequest,
  payloadToActor,

  // Password hashing
  hashPassword,
  verifyPassword,
  needsRehash,
  validatePasswordStrength,

  // Fastify integration
  registerAuthHooks,
  requireAuth,
  withRequestContext,
  registerJwtPlugin,
} from "@saas-studio/identity";
```

### Usage

```typescript
// In route handler
fastify.get("/items", async (request) => {
  requireAuth(request);

  return withRequestContext(request, async (ctx) => {
    const tenantId = ctx.tenantId;
    const actor = ctx.actor;

    // Access context anywhere in the call stack
    const items = await itemService.list();
    return { data: items };
  });
});

// Password handling
const hash = await hashPassword("user-password");
const valid = await verifyPassword("user-password", hash);
```

---

## @saas-studio/tenancy

**Purpose**: Automatic tenant scoping for Prisma queries.

### Key Exports

```typescript
import {
  // Resolvers
  HeaderTenantResolver,
  SubdomainTenantResolver,
  PathTenantResolver,
  JwtTenantResolver,
  CompositeTenantResolver,
  createDefaultResolver,

  // Prisma extension
  createTenantScopeExtension,
  withTenantScope,
  tenantWhere,

  // Fastify integration
  createTenantHook,
  registerTenantHook,
  getRequestTenantId,
  requireRequestTenantId,
  validateTenantAccess,
} from "@saas-studio/tenancy";
```

### Usage

```typescript
// Create tenant-scoped Prisma client
const prisma = new PrismaClient().$extends(
  createTenantScopeExtension({
    excludedModels: ["Tenant", "AuditLog", "Outbox"],
  }),
);

// All queries are now automatically scoped
const items = await prisma.item.findMany();
// → SELECT * FROM items WHERE tenant_id = 'current-tenant-id'

// Register tenant resolution hook
registerTenantHook(app, {
  resolver: createDefaultResolver("example.com"),
  required: true,
});
```

---

## @saas-studio/db

**Purpose**: Prisma client utilities and repository patterns.

### Key Exports

```typescript
import {
  // Client
  createDatabaseClient,
  createStandardDatabaseClient,
  checkDatabaseConnection,
  disconnectDatabase,

  // Repositories
  BaseRepository,
  TenantScopedRepository,

  // Transactions
  TransactionManager,
  createTransactionManager,
  BatchOperations,
  createBatchOperations,

  // Specification pattern
  PrismaSpecification,

  // Types
  IRepository,
  PaginationOptions,
  PaginatedResult,
  SortOptions,
  FilterOptions,

  // Prisma re-exports
  PrismaClient,
  Prisma,
} from "@saas-studio/db";
```

### Usage

```typescript
// Create repository
class PrismaItemRepository extends TenantScopedRepository<Item, ItemProps> {
  constructor(prisma: PrismaClient) {
    super(prisma, "item");
  }

  async findByStatus(status: string): Promise<Item[]> {
    const records = await this.prisma.item.findMany({
      where: { status },
    });
    return records.map(this.toDomain);
  }
}

// Batch operations
const batch = createBatchOperations(prisma);
await batch.createMany("item", items);
```

---

## @saas-studio/rbac

**Purpose**: Role-based access control with permissions and policies.

### Key Exports

```typescript
import {
  // Permissions
  permission,
  crudPermissions,
  PermissionRegistry,
  permissionRegistry,
  checkPermission,
  requirePermission,
  checkAnyPermission,
  checkAllPermissions,

  // Roles
  RoleRegistry,
  roleRegistry,
  SystemRoles,
  checkRole,
  requireRole,
  checkAnyRole,
  checkAllRoles,
  isSuperAdmin,
  isAdmin,
  getEffectivePermissions,

  // Policies
  PolicyEvaluator,
  policyEvaluator,
  PolicyBuilder,
  definePolicy,

  // Guards (Fastify)
  permissionGuard,
  anyPermissionGuard,
  allPermissionsGuard,
  roleGuard,
  anyRoleGuard,
  policyGuard,

  // Audit logging
  configureAuthorizationAuditLogger,
  getAuthorizationAuditLogger,
  AuthorizationAuditLogger,
  AuthorizationAuditEntry,
} from "@saas-studio/rbac";
```

### Usage

```typescript
// Register permissions
permissionRegistry.registerCrud("items");
permissionRegistry.register("items:publish");

// Register roles
roleRegistry.register({
  name: "editor",
  permissions: ["items:read", "items:update", "items:list"],
  inherits: ["viewer"],
});

// Use guards in routes
fastify.post(
  "/items",
  {
    preHandler: [permissionGuard(permission("items", "create"))],
  },
  handler,
);

fastify.delete(
  "/items/:id",
  {
    preHandler: [roleGuard("admin")],
  },
  handler,
);
```

---

## @saas-studio/audit

**Purpose**: Append-only, immutable audit logging.

### Key Exports

```typescript
import {
  // Types
  AuditAction,
  AuditActorType,

  // Schemas
  AuditEntrySchema,
  CreateAuditEntrySchema,
  AuditQueryParamsSchema,

  // Writer
  AuditWriter,
  AuditEntryBuilder,
  auditEntry,
  createAuditWriter,
} from "@saas-studio/audit";
```

### Usage

```typescript
// Create audit entry with builder
const entry = auditEntry()
  .tenant(tenantId)
  .action("CREATE")
  .aggregate("Item", item.id)
  .actor("user", userId)
  .after(item.toPersistence())
  .build();

// Write in transaction (via UnitOfWork)
await unitOfWork.execute(async (tx) => {
  const saved = await itemRepository.save(item, tx);
  return {
    result: saved,
    auditEntries: [entry],
    outboxEntries: [],
  };
});
```

---

## @saas-studio/outbox

**Purpose**: Transactional outbox pattern for reliable event publishing.

### Key Exports

```typescript
import {
  // Schema
  OutboxStatus,
  OutboxEntrySchema,
  CreateOutboxEntrySchema,

  // Writer
  OutboxWriter,
  OutboxEntryBuilder,
  outboxEntry,
  createOutboxWriter,

  // Unit of Work
  UnitOfWork,
  createUnitOfWork,

  // Publishers
  NatsPublisher,
  InMemoryPublisher,
  createNatsPublisher,
  createInMemoryPublisher,

  // Worker
  OutboxWorker,
  createOutboxWorker,
} from "@saas-studio/outbox";
```

### Usage

```typescript
// Create unit of work
const unitOfWork = createUnitOfWork(prisma);

// Execute transactional operation
const result = await unitOfWork.execute(async (tx) => {
  const item = await itemRepository.save(newItem, tx);

  return {
    result: item,
    auditEntries: [
      auditEntry()
        .tenant(tenantId)
        .action("CREATE")
        .aggregate("Item", item.id)
        .after(item.toPersistence())
        .build(),
    ],
    outboxEntries: [
      outboxEntry()
        .tenant(tenantId)
        .event("item.created")
        .aggregate("Item", item.id)
        .payload(item.toPersistence())
        .build(),
    ],
  };
});

// Start outbox worker (separate process)
const worker = createOutboxWorker(prisma, {
  publisher: createNatsPublisher(natsConnection),
  pollInterval: 1000,
});
await worker.start();
```

---

## @saas-studio/events

**Purpose**: Event bus abstraction for domain and integration events.

### Key Exports

```typescript
import {
  // Event bus implementations
  InMemoryEventBus,
  NatsEventBus,
  createNatsEventBus,

  // Integration
  DomainToIntegrationAdapter,
  EventBusDispatcher,
  InMemoryEventStore,

  // Types
  IEventBus,
  EventHandler,
  EventSubscription,
  IEventStore,
} from "@saas-studio/events";
```

### Usage

```typescript
// Create event bus
const eventBus = await createNatsEventBus({
  servers: ["nats://localhost:4222"],
});

// Subscribe to events
await eventBus.subscribe("item.created", async (event) => {
  console.log("Item created:", event.payload);
});

// Publish event
await eventBus.publish({
  type: "item.created",
  payload: item.toPersistence(),
});
```

---

## @saas-studio/jobs

**Purpose**: Background job processing with BullMQ.

### Key Exports

```typescript
import {
  // Types
  BaseJobDataSchema,
  JobStatus,
  success,
  failure,

  // Queue
  createQueue,
  TypedQueue,

  // Worker
  createWorker,
  TypedWorker,

  // Scheduler
  createScheduler,
  JobScheduler,
  CronPatterns,

  // Fastify integration
  registerJobsPlugin,
  decorateWithQueues,

  // Helpers
  defineJob,
} from "@saas-studio/jobs";
```

### Usage

```typescript
// Define a job
const SendEmailJob = defineJob({
  name: "send-email",
  schema: z.object({
    to: z.string().email(),
    subject: z.string(),
    body: z.string(),
  }),
});

// Create queue
const emailQueue = createQueue("emails", { connection: redis });

// Create worker
const worker = createWorker(
  "emails",
  async (job) => {
    const { to, subject, body } = job.data;
    await sendEmail(to, subject, body);
    return success({ sent: true });
  },
  { connection: redis },
);

// Add job
await emailQueue.add("send-email", {
  to: "user@example.com",
  subject: "Welcome",
  body: "Hello!",
});

// Schedule recurring job
const scheduler = createScheduler(emailQueue);
scheduler.schedule("daily-digest", CronPatterns.DAILY_MIDNIGHT, {
  type: "digest",
});
```

---

## @saas-studio/observability

**Purpose**: OpenTelemetry tracing, metrics, and monitoring.

### Key Exports

```typescript
import {
  // Tracing
  initTracing,
  shutdownTracing,
  getTracer,
  withSpan,
  addSpanAttributes,
  recordSpanEvent,
  getCurrentTraceId,
  getCurrentSpanId,

  // Metrics
  initMetrics,
  shutdownMetrics,
  getMeter,
  createAppMetrics,

  // Fastify integration
  registerObservabilityHooks,
  healthHandler,
  createReadinessHandler,

  // Prisma integration
  createPrismaMiddleware,
  logPrismaQuery,

  // Unified init
  initObservability,
  shutdownObservability,
} from "@saas-studio/observability";
```

### Usage

```typescript
// Initialize observability
await initObservability({
  serviceName: "my-service",
  serviceVersion: "1.0.0",
});

// Custom span
await withSpan("process-document", async (span) => {
  span.setAttribute("document.id", documentId);
  await processDocument(documentId);
});

// Metrics
const metrics = createAppMetrics();
metrics.httpRequestsTotal.add(1, { method: "GET", path: "/items" });

// Register Fastify hooks
registerObservabilityHooks(app, {
  logger,
  metrics,
  ignorePaths: ["/health", "/ready"],
});
```

---

## @saas-studio/realtime

**Purpose**: WebSocket gateway for real-time event streaming.

### Key Exports

```typescript
import {
  // Subscriptions
  SubscriptionManager,
  createSubscriptionManager,

  // Authentication
  JwtWsTokenVerifier,
  extractWsToken,
  extractWsTokenWithSource, // Returns token with source info
  authenticateWsConnection,
  requireWsAuth,
  createJwtWsVerifier,
  TokenExtractionResult,

  // Gateway
  WebSocketGateway,
  WsMessageType,
  createWebSocketGateway,
} from "@saas-studio/realtime";
```

### Usage

```typescript
// Create gateway
const gateway = createWebSocketGateway(app, {
  path: "/ws",
  verifier: createJwtWsVerifier(jwtSecret),
});

// Broadcast to tenant
gateway.broadcastToTenant(tenantId, {
  type: "item.created",
  payload: item,
});

// Client connection (prefer Authorization header over query param)
// Token extraction priority: Authorization header > Sec-WebSocket-Protocol > query param
const ws = new WebSocket("ws://localhost:3000/ws", ["token.JWT_TOKEN"]);
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log("Received:", message);
};
```

---

## @saas-studio/api-factory

**Purpose**: Pre-configured Fastify factory with all middleware.

### Key Exports

```typescript
import {
  // Factory
  createApiFactory,
  createMinimalApiFactory,

  // Plugins
  registerCors,
  registerHelmet,
  registerRateLimit,
  registerSensible,
  registerSwagger,
  registerHealthChecks,

  // Middleware
  registerCorrelationId,
  registerRequestLogging,
  registerGracefulShutdown,

  // Error handling
  registerErrorHandler,
  registerNotFoundHandler,
} from "@saas-studio/api-factory";
```

### Usage

```typescript
const { app, logger, start, stop } = await createApiFactory({
  name: "my-service",
  version: "1.0.0",
  port: 3000,
  logLevel: "info",
  logPretty: true,

  jwt: {
    secret: process.env.JWT_SECRET,
  },

  cors: {
    origins: ["http://localhost:3000"],
  },

  rateLimit: {
    max: 100,
    timeWindow: "1 minute",
  },

  swagger: {
    title: "My Service API",
    description: "API documentation",
    version: "1.0.0",
  },

  healthChecks: {
    readyChecks: {
      database: async () => {
        await prisma.$queryRaw`SELECT 1`;
        return true;
      },
    },
  },
});

// Register routes
app.get("/items", handler);

// Start server
await start();
```

# Services Guide

This document describes each microservice in SaaS Studio.

## Overview

| Service           | Port | Description                             |
| ----------------- | ---- | --------------------------------------- |
| **media-service** | 3001 | File uploads, image processing, storage |
| **form-service**  | 3002 | Dynamic forms, validation, submissions  |
| **mail-service**  | 3003 | Email templates, sending, delivery      |
| **pdf-service**   | 3004 | PDF generation, templates               |

All services follow the same DDD/Onion architecture pattern and share foundation packages.

---

## Media Service

**Port**: 3001

**Purpose**: Handle file uploads, image processing, and storage management.

### Domain Model

```typescript
// MediaFile entity
interface MediaFile {
  id: string;
  tenantId: string;
  name: string;
  originalName: string;
  mimeType: string;
  size: bigint;
  path: string;
  bucket: string;
  url: string | null;
  thumbnailUrl: string | null;
  metadata: Record<string, unknown> | null;
  status: "pending" | "processing" | "ready" | "failed" | "archived";
  version: number;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}
```

### API Endpoints

| Method | Path         | Description       | Permission     |
| ------ | ------------ | ----------------- | -------------- |
| GET    | `/media`     | List media files  | `media:list`   |
| GET    | `/media/:id` | Get media file    | `media:read`   |
| POST   | `/media`     | Create media file | `media:create` |
| PATCH  | `/media/:id` | Update media file | `media:update` |
| DELETE | `/media/:id` | Delete media file | `media:delete` |

### Request/Response Examples

**Create Media File**

```bash
POST /media
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-ID: <tenant-id>

{
  "name": "profile-photo.jpg",
  "originalName": "IMG_1234.jpg",
  "mimeType": "image/jpeg",
  "size": 1024000,
  "path": "uploads/2024/01/abc123.jpg",
  "bucket": "media-bucket"
}
```

**Response**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenantId": "tenant-123",
    "name": "profile-photo.jpg",
    "originalName": "IMG_1234.jpg",
    "mimeType": "image/jpeg",
    "size": "1024000",
    "path": "uploads/2024/01/abc123.jpg",
    "bucket": "media-bucket",
    "url": null,
    "thumbnailUrl": null,
    "metadata": null,
    "status": "pending",
    "version": 0,
    "createdBy": "user-456",
    "createdAt": "2024-01-15T10:30:00.000Z",
    "updatedAt": "2024-01-15T10:30:00.000Z"
  }
}
```

### Features

- **File Status Lifecycle**: pending → processing → ready (or failed)
- **Image Detection**: Automatic detection of image MIME types
- **Thumbnails**: Support for thumbnail URL storage
- **Metadata**: Flexible JSON metadata field
- **Soft Delete**: Files are archived, not permanently deleted

---

## Form Service

**Port**: 3002

**Purpose**: Create dynamic forms with validation and handle submissions.

### Domain Models

```typescript
// Form entity
interface Form {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  schema: FormSchema;
  settings: FormSettings | null;
  status: "draft" | "published" | "archived";
  version: number;
  publishedAt: Date | null;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// FormSchema
interface FormSchema {
  fields: FormField[];
  sections?: Array<{
    id: string;
    title: string;
    description?: string;
    fields: string[];
  }>;
}

// FormField
interface FormField {
  id: string;
  name: string;
  label: string;
  type: FieldType;
  placeholder?: string;
  defaultValue?: unknown;
  required: boolean;
  validation?: FieldValidation;
  options?: Array<{ value: string; label: string }>;
  conditionalLogic?: ConditionalLogic;
}

// FieldType
type FieldType =
  | "text"
  | "textarea"
  | "number"
  | "email"
  | "phone"
  | "date"
  | "time"
  | "datetime"
  | "select"
  | "multiselect"
  | "checkbox"
  | "radio"
  | "file"
  | "hidden";

// FormSubmission entity
interface FormSubmission {
  id: string;
  tenantId: string;
  formId: string;
  data: Record<string, unknown>;
  metadata: Record<string, unknown> | null;
  status: "pending" | "processed" | "rejected" | "spam";
  submittedBy: string | null;
  submittedAt: Date;
  processedAt: Date | null;
}
```

### API Endpoints

| Method | Path                     | Description      | Permission                 |
| ------ | ------------------------ | ---------------- | -------------------------- |
| GET    | `/forms`                 | List forms       | `forms:list`               |
| GET    | `/forms/:id`             | Get form         | `forms:read`               |
| POST   | `/forms`                 | Create form      | `forms:create`             |
| PATCH  | `/forms/:id`             | Update form      | `forms:update`             |
| DELETE | `/forms/:id`             | Delete form      | `forms:delete`             |
| POST   | `/forms/:id/publish`     | Publish form     | `forms:update`             |
| POST   | `/forms/:id/submit`      | Submit form      | (public or `forms:submit`) |
| GET    | `/forms/:id/submissions` | List submissions | `forms:read`               |

### Request/Response Examples

**Create Form**

```bash
POST /forms
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Contact Form",
  "description": "General contact form",
  "schema": {
    "fields": [
      {
        "id": "name",
        "name": "name",
        "label": "Full Name",
        "type": "text",
        "required": true,
        "validation": {
          "minLength": 2,
          "maxLength": 100
        }
      },
      {
        "id": "email",
        "name": "email",
        "label": "Email Address",
        "type": "email",
        "required": true
      },
      {
        "id": "message",
        "name": "message",
        "label": "Message",
        "type": "textarea",
        "required": true,
        "validation": {
          "minLength": 10,
          "maxLength": 1000
        }
      }
    ]
  },
  "settings": {
    "submitButtonText": "Send Message",
    "successMessage": "Thank you for your message!",
    "notifyOnSubmission": true,
    "notificationEmails": ["admin@example.com"]
  }
}
```

**Submit Form**

```bash
POST /forms/:id/submit
Content-Type: application/json

{
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "I have a question about your services."
  },
  "metadata": {
    "source": "website",
    "userAgent": "Mozilla/5.0..."
  }
}
```

### Features

- **14 Field Types**: text, textarea, number, email, phone, date, time, datetime, select, multiselect, checkbox, radio, file, hidden
- **Validation Rules**: minLength, maxLength, min, max, pattern
- **Conditional Logic**: Show/hide fields based on other field values
- **Form Sections**: Organize fields into logical sections
- **Publication Workflow**: Forms must be published before accepting submissions
- **Submission Tracking**: Track status (pending, processed, rejected, spam)

---

## Mail Service

**Port**: 3003

**Purpose**: Send emails with templates and queue-based delivery.

### Domain Models

```typescript
// EmailTemplate entity
interface EmailTemplate {
  id: string;
  tenantId: string;
  name: string;
  subject: string;
  htmlBody: string;
  textBody: string | null;
  variables: TemplateVariable[] | null;
  category: string | null;
  status: "active" | "inactive" | "archived";
  version: number;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// TemplateVariable
interface TemplateVariable {
  name: string;
  description?: string;
  required: boolean;
  defaultValue?: string;
}

// Email entity
interface Email {
  id: string;
  tenantId: string;
  templateId: string | null;
  fromAddress: string;
  fromName: string | null;
  toAddresses: string[];
  ccAddresses: string[] | null;
  bccAddresses: string[] | null;
  subject: string;
  htmlBody: string | null;
  textBody: string | null;
  attachments: EmailAttachment[] | null;
  metadata: Record<string, unknown> | null;
  status: "pending" | "queued" | "sending" | "sent" | "failed" | "bounced";
  priority: number;
  scheduledFor: Date | null;
  sentAt: Date | null;
  failedAt: Date | null;
  failureReason: string | null;
  retryCount: number;
  maxRetries: number;
  createdBy: string | null;
  createdAt: Date;
}
```

### API Endpoints

| Method | Path                  | Description     | Permission              |
| ------ | --------------------- | --------------- | ----------------------- |
| GET    | `/mail/templates`     | List templates  | `mail-templates:list`   |
| GET    | `/mail/templates/:id` | Get template    | `mail-templates:read`   |
| POST   | `/mail/templates`     | Create template | `mail-templates:create` |
| PATCH  | `/mail/templates/:id` | Update template | `mail-templates:update` |
| DELETE | `/mail/templates/:id` | Delete template | `mail-templates:delete` |
| GET    | `/mail/emails`        | List emails     | `mail:list`             |
| GET    | `/mail/emails/:id`    | Get email       | `mail:read`             |
| POST   | `/mail/send`          | Send email      | `mail:send`             |

### Request/Response Examples

**Create Template**

```bash
POST /mail/templates
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "welcome-email",
  "subject": "Welcome to {{company}}!",
  "htmlBody": "<h1>Welcome, {{firstName}}!</h1><p>Thank you for joining {{company}}.</p>",
  "textBody": "Welcome, {{firstName}}! Thank you for joining {{company}}.",
  "variables": [
    { "name": "firstName", "required": true },
    { "name": "company", "required": true, "defaultValue": "Our Platform" }
  ],
  "category": "onboarding"
}
```

**Send Email with Template**

```bash
POST /mail/send
Content-Type: application/json
Authorization: Bearer <token>

{
  "templateId": "template-123",
  "fromAddress": "noreply@example.com",
  "fromName": "Example App",
  "toAddresses": ["user@example.com"],
  "data": {
    "firstName": "John",
    "company": "Example Corp"
  },
  "priority": 1
}
```

**Send Email without Template**

```bash
POST /mail/send
Content-Type: application/json
Authorization: Bearer <token>

{
  "fromAddress": "noreply@example.com",
  "toAddresses": ["user@example.com"],
  "subject": "Important Update",
  "htmlBody": "<p>Hello! This is an important update.</p>",
  "textBody": "Hello! This is an important update."
}
```

### Features

- **Template Variables**: `{{variable}}` syntax for dynamic content
- **Multi-Recipient**: Support for to, cc, bcc addresses
- **Attachments**: Send files with emails
- **Priority Queue**: Higher priority emails sent first
- **Scheduling**: Schedule emails for future delivery
- **Retry Logic**: Automatic retries on failure (max 3 by default)
- **Status Tracking**: pending → queued → sending → sent (or failed/bounced)

---

## PDF Service

**Port**: 3004

**Purpose**: Generate PDFs from HTML templates.

### Domain Models

```typescript
// PdfTemplate entity
interface PdfTemplate {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  htmlContent: string;
  cssStyles: string | null;
  variables: TemplateVariable[] | null;
  pageSize: "A4" | "A3" | "Letter" | "Legal" | "Tabloid";
  orientation: "portrait" | "landscape";
  margins: PageMargins | null;
  header: string | null;
  footer: string | null;
  status: "active" | "inactive" | "archived";
  version: number;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// PageMargins
interface PageMargins {
  top: string;
  right: string;
  bottom: string;
  left: string;
}

// PdfDocument entity
interface PdfDocument {
  id: string;
  tenantId: string;
  templateId: string | null;
  name: string;
  data: Record<string, unknown> | null;
  filePath: string | null;
  fileSize: bigint | null;
  pageCount: number | null;
  status: "pending" | "generating" | "ready" | "failed" | "expired";
  generatedAt: Date | null;
  expiresAt: Date | null;
  metadata: Record<string, unknown> | null;
  createdBy: string | null;
  createdAt: Date;
}
```

### API Endpoints

| Method | Path                 | Description     | Permission             |
| ------ | -------------------- | --------------- | ---------------------- |
| GET    | `/pdf/templates`     | List templates  | `pdf-templates:list`   |
| GET    | `/pdf/templates/:id` | Get template    | `pdf-templates:read`   |
| POST   | `/pdf/templates`     | Create template | `pdf-templates:create` |
| PATCH  | `/pdf/templates/:id` | Update template | `pdf-templates:update` |
| DELETE | `/pdf/templates/:id` | Delete template | `pdf-templates:delete` |
| GET    | `/pdf/documents`     | List documents  | `pdf:list`             |
| GET    | `/pdf/documents/:id` | Get document    | `pdf:read`             |
| POST   | `/pdf/generate`      | Generate PDF    | `pdf:generate`         |
| DELETE | `/pdf/documents/:id` | Delete document | `pdf:delete`           |

### Request/Response Examples

**Create Template**

```bash
POST /pdf/templates
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "invoice-template",
  "description": "Standard invoice template",
  "htmlContent": "<div class=\"invoice\"><h1>Invoice #{{invoiceNumber}}</h1><p>To: {{customerName}}</p><table>{{#items}}<tr><td>{{name}}</td><td>{{price}}</td></tr>{{/items}}</table><p><strong>Total: {{total}}</strong></p></div>",
  "cssStyles": ".invoice { font-family: Arial; } table { width: 100%; }",
  "variables": [
    { "name": "invoiceNumber", "required": true },
    { "name": "customerName", "required": true },
    { "name": "items", "required": true },
    { "name": "total", "required": true }
  ],
  "pageSize": "A4",
  "orientation": "portrait",
  "margins": {
    "top": "20mm",
    "right": "15mm",
    "bottom": "20mm",
    "left": "15mm"
  },
  "footer": "<div style=\"text-align: center;\">Page {{page}} of {{pages}}</div>"
}
```

**Generate PDF**

```bash
POST /pdf/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "templateId": "template-123",
  "name": "Invoice-2024-001.pdf",
  "data": {
    "invoiceNumber": "2024-001",
    "customerName": "Acme Corp",
    "items": [
      { "name": "Widget A", "price": "$100" },
      { "name": "Widget B", "price": "$200" }
    ],
    "total": "$300"
  },
  "expiresAt": "2024-02-15T00:00:00Z"
}
```

**Response (202 Accepted)**

```json
{
  "data": {
    "id": "doc-123",
    "tenantId": "tenant-456",
    "templateId": "template-123",
    "name": "Invoice-2024-001.pdf",
    "status": "pending",
    "createdAt": "2024-01-15T10:30:00.000Z"
  }
}
```

### Features

- **HTML to PDF**: Convert HTML/CSS to PDF using Puppeteer
- **Template Variables**: `{{variable}}` syntax for dynamic content
- **Page Sizes**: A4, A3, Letter, Legal, Tabloid
- **Orientation**: Portrait or Landscape
- **Margins**: Configurable page margins
- **Headers/Footers**: Custom header and footer content
- **Page Numbers**: `{{page}}` and `{{pages}}` variables in headers/footers
- **Expiration**: Set document expiration dates
- **Async Generation**: Returns 202 Accepted, generates in background

---

## Common Patterns

### Service Bootstrap

All services follow this pattern in `main.ts`:

```typescript
async function bootstrap(): Promise<void> {
  // 1. Create Prisma client with tenant scoping
  const prisma = new PrismaClient().$extends(
    createTenantScopeExtension({
      excludedModels: ["Tenant", "AuditLog", "Outbox"],
    }),
  ) as unknown as PrismaClient;

  // 2. Register permissions
  permissionRegistry.registerCrud("resource");

  // 3. Register roles
  roleRegistry.register({
    name: "admin",
    permissions: crudPermissions("resource"),
  });

  // 4. Create API factory
  const { app, logger, start } = await createApiFactory({
    name: "service-name",
    version: "0.1.0",
    port: 3001,
    jwt: { secret: process.env["JWT_SECRET"] },
    swagger: { title: "Service API" },
    healthChecks: {
      readyChecks: {
        database: async () => {
          await prisma.$queryRaw`SELECT 1`;
          return true;
        },
      },
    },
  });

  // 5. Create dependencies
  const unitOfWork = createUnitOfWork(prisma);
  const repository = new PrismaRepository(prisma);

  // 6. Register routes
  registerRoutes(app, { repository, unitOfWork });

  // 7. Graceful shutdown
  app.addHook("onClose", async () => {
    await prisma.$disconnect();
  });

  // 8. Start server
  await start();
}
```

### Route Handler Pattern

```typescript
fastify.post<{ Body: CreateRequest }>(
  "/resource",
  {
    preHandler: [permissionGuard(permission("resource", "create"))],
  },
  async (request, reply) => {
    requireAuth(request);

    return withRequestContext(request, async (ctx) => {
      const body = CreateRequestSchema.parse(request.body);

      const entity = Entity.create({
        tenantId: ctx.tenantId,
        ...body,
        createdBy: ctx.actor?.id,
      });

      const saved = await unitOfWork.execute(async (tx) => {
        const result = await repository.save(entity, tx);
        return {
          result,
          auditEntries: [],
          outboxEntries: [],
        };
      });

      reply.status(201);
      return { data: toResponse(saved) };
    });
  },
);
```

### Database Schema Pattern

Each service includes these shared tables:

```prisma
model AuditLog {
  id            String   @id @default(uuid())
  tenantId      String   @map("tenant_id")
  aggregateType String   @map("aggregate_type")
  aggregateId   String   @map("aggregate_id")
  action        String
  actorType     String   @map("actor_type")
  actorId       String?  @map("actor_id")
  before        Json?
  after         Json?
  metadata      Json?
  correlationId String?  @map("correlation_id")
  occurredAt    DateTime @default(now()) @map("occurred_at")

  @@map("audit_log")
}

model Outbox {
  id            String    @id @default(uuid())
  tenantId      String    @map("tenant_id")
  eventType     String    @map("event_type")
  aggregateType String    @map("aggregate_type")
  aggregateId   String    @map("aggregate_id")
  payload       Json
  metadata      Json?
  status        String    @default("pending")
  retryCount    Int       @default(0) @map("retry_count")
  maxRetries    Int       @default(3) @map("max_retries")
  lastError     String?   @map("last_error")
  correlationId String?   @map("correlation_id")
  scheduledFor  DateTime? @map("scheduled_for")
  processedAt   DateTime? @map("processed_at")
  createdAt     DateTime  @default(now()) @map("created_at")

  @@map("outbox")
}
```
