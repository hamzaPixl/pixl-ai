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

| Layer | Can Depend On | Cannot Depend On |
|-------|---------------|------------------|
| API | Application, Domain | Infrastructure (directly) |
| Application | Domain | Infrastructure (directly) |
| Domain | Nothing (pure) | Prisma, Fastify, external libs |
| Infrastructure | Domain | API, Application |

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
const resolver = new HeaderTenantResolver('X-Tenant-ID');

// Subdomain-based (tenant.example.com)
const resolver = new SubdomainTenantResolver('example.com');

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
    excludedModels: ['Tenant', 'AuditLog', 'Outbox'],
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
type ActorType = 'user' | 'system' | 'service' | 'anonymous';

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
  const item = Item.create({ name: 'New Item', tenantId });
  const saved = await itemRepository.save(item, tx);

  return {
    result: saved,
    // 2. Audit entry (written in same transaction)
    auditEntries: [{
      action: 'CREATE',
      aggregateType: 'Item',
      aggregateId: saved.id,
      after: saved.toPersistence(),
    }],
    // 3. Outbox entry (written in same transaction)
    outboxEntries: [{
      eventType: 'item.created',
      aggregateType: 'Item',
      aggregateId: saved.id,
      payload: saved.toPersistence(),
    }],
  };
});
```

## RBAC (Role-Based Access Control)

### Permission Model

Permissions follow the format: `resource:action`

```typescript
// Built-in CRUD permissions
const permissions = crudPermissions('items');
// ['items:create', 'items:read', 'items:update', 'items:delete', 'items:list']

// Custom permissions
permissionRegistry.register('items:publish');
permissionRegistry.register('items:archive');
```

### Role Hierarchy

```typescript
roleRegistry.register({
  name: 'admin',
  permissions: crudPermissions('items'),
});

roleRegistry.register({
  name: 'editor',
  permissions: ['items:read', 'items:update', 'items:list'],
  inherits: ['viewer'],
});

roleRegistry.register({
  name: 'viewer',
  permissions: ['items:read', 'items:list'],
});
```

### Route Guards

```typescript
fastify.post('/items', {
  preHandler: [permissionGuard(permission('items', 'create'))],
}, async (request, reply) => {
  // Only accessible with items:create permission
});
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
    super(`${resource} with id ${id} not found`, 'NOT_FOUND');
  }
}

export class ValidationError extends DomainError {
  constructor(message: string, details: ValidationDetail[]) {
    super(message, 'VALIDATION_ERROR');
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
  serviceName: 'item-service',
  version: '1.0.0',
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
