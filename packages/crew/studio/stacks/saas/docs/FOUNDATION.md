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
import { UuidSchema, EmailSchema, TimestampSchema } from '@saas-studio/contracts';

// Branded types (type-safe IDs)
import { TenantIdSchema, CorrelationIdSchema, type TenantId } from '@saas-studio/contracts';

// Base schemas
import { TenantScopedSchema, TimestampedSchema, BaseEntitySchema } from '@saas-studio/contracts';

// Event envelope
import { EventEnvelopeSchema, EventMetadataSchema } from '@saas-studio/contracts';

// Pagination
import { PaginationParamsSchema, PaginatedResponseSchema } from '@saas-studio/contracts';

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
} from '@saas-studio/contracts';
```

### Usage

```typescript
// Validate input
const id = UuidSchema.parse(input.id);

// Create typed IDs
const tenantId = TenantIdSchema.parse('550e8400-e29b-41d4-a716-446655440000');

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
} from '@saas-studio/config';
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
  serviceName: 'my-service',
  version: '1.0.0',
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
} from '@saas-studio/logger';
```

### Usage

```typescript
// Create logger
const logger = createLogger({
  serviceName: 'my-service',
  serviceVersion: '1.0.0',
  level: 'info',
  pretty: process.env.NODE_ENV !== 'production',
});

// Log with context
logger.info('User created', { userId: '123', email: 'user@example.com' });
logger.error('Operation failed', { error, tenantId });

// Create child logger for request
const reqLogger = createRequestLogger(logger, {
  correlationId: 'req-123',
  tenantId: 'tenant-456',
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
} from '@saas-studio/domain';
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
} from '@saas-studio/identity';
```

### Usage

```typescript
// In route handler
fastify.get('/items', async (request) => {
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
const hash = await hashPassword('user-password');
const valid = await verifyPassword('user-password', hash);
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
} from '@saas-studio/tenancy';
```

### Usage

```typescript
// Create tenant-scoped Prisma client
const prisma = new PrismaClient().$extends(
  createTenantScopeExtension({
    excludedModels: ['Tenant', 'AuditLog', 'Outbox'],
  }),
);

// All queries are now automatically scoped
const items = await prisma.item.findMany();
// → SELECT * FROM items WHERE tenant_id = 'current-tenant-id'

// Register tenant resolution hook
registerTenantHook(app, {
  resolver: createDefaultResolver('example.com'),
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
} from '@saas-studio/db';
```

### Usage

```typescript
// Create repository
class PrismaItemRepository extends TenantScopedRepository<Item, ItemProps> {
  constructor(prisma: PrismaClient) {
    super(prisma, 'item');
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
await batch.createMany('item', items);
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
} from '@saas-studio/rbac';
```

### Usage

```typescript
// Register permissions
permissionRegistry.registerCrud('items');
permissionRegistry.register('items:publish');

// Register roles
roleRegistry.register({
  name: 'editor',
  permissions: ['items:read', 'items:update', 'items:list'],
  inherits: ['viewer'],
});

// Use guards in routes
fastify.post('/items', {
  preHandler: [permissionGuard(permission('items', 'create'))],
}, handler);

fastify.delete('/items/:id', {
  preHandler: [roleGuard('admin')],
}, handler);
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
} from '@saas-studio/audit';
```

### Usage

```typescript
// Create audit entry with builder
const entry = auditEntry()
  .tenant(tenantId)
  .action('CREATE')
  .aggregate('Item', item.id)
  .actor('user', userId)
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
} from '@saas-studio/outbox';
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
        .action('CREATE')
        .aggregate('Item', item.id)
        .after(item.toPersistence())
        .build(),
    ],
    outboxEntries: [
      outboxEntry()
        .tenant(tenantId)
        .event('item.created')
        .aggregate('Item', item.id)
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
} from '@saas-studio/events';
```

### Usage

```typescript
// Create event bus
const eventBus = await createNatsEventBus({
  servers: ['nats://localhost:4222'],
});

// Subscribe to events
await eventBus.subscribe('item.created', async (event) => {
  console.log('Item created:', event.payload);
});

// Publish event
await eventBus.publish({
  type: 'item.created',
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
} from '@saas-studio/jobs';
```

### Usage

```typescript
// Define a job
const SendEmailJob = defineJob({
  name: 'send-email',
  schema: z.object({
    to: z.string().email(),
    subject: z.string(),
    body: z.string(),
  }),
});

// Create queue
const emailQueue = createQueue('emails', { connection: redis });

// Create worker
const worker = createWorker('emails', async (job) => {
  const { to, subject, body } = job.data;
  await sendEmail(to, subject, body);
  return success({ sent: true });
}, { connection: redis });

// Add job
await emailQueue.add('send-email', {
  to: 'user@example.com',
  subject: 'Welcome',
  body: 'Hello!',
});

// Schedule recurring job
const scheduler = createScheduler(emailQueue);
scheduler.schedule('daily-digest', CronPatterns.DAILY_MIDNIGHT, {
  type: 'digest',
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
} from '@saas-studio/observability';
```

### Usage

```typescript
// Initialize observability
await initObservability({
  serviceName: 'my-service',
  serviceVersion: '1.0.0',
});

// Custom span
await withSpan('process-document', async (span) => {
  span.setAttribute('document.id', documentId);
  await processDocument(documentId);
});

// Metrics
const metrics = createAppMetrics();
metrics.httpRequestsTotal.add(1, { method: 'GET', path: '/items' });

// Register Fastify hooks
registerObservabilityHooks(app, {
  logger,
  metrics,
  ignorePaths: ['/health', '/ready'],
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
  extractWsTokenWithSource,  // Returns token with source info
  authenticateWsConnection,
  requireWsAuth,
  createJwtWsVerifier,
  TokenExtractionResult,

  // Gateway
  WebSocketGateway,
  WsMessageType,
  createWebSocketGateway,
} from '@saas-studio/realtime';
```

### Usage

```typescript
// Create gateway
const gateway = createWebSocketGateway(app, {
  path: '/ws',
  verifier: createJwtWsVerifier(jwtSecret),
});

// Broadcast to tenant
gateway.broadcastToTenant(tenantId, {
  type: 'item.created',
  payload: item,
});

// Client connection (prefer Authorization header over query param)
// Token extraction priority: Authorization header > Sec-WebSocket-Protocol > query param
const ws = new WebSocket('ws://localhost:3000/ws', ['token.JWT_TOKEN']);
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
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
} from '@saas-studio/api-factory';
```

### Usage

```typescript
const { app, logger, start, stop } = await createApiFactory({
  name: 'my-service',
  version: '1.0.0',
  port: 3000,
  logLevel: 'info',
  logPretty: true,

  jwt: {
    secret: process.env.JWT_SECRET,
  },

  cors: {
    origins: ['http://localhost:3000'],
  },

  rateLimit: {
    max: 100,
    timeWindow: '1 minute',
  },

  swagger: {
    title: 'My Service API',
    description: 'API documentation',
    version: '1.0.0',
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
app.get('/items', handler);

// Start server
await start();
```
