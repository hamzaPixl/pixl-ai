# Database Patterns

## Prisma Best Practices

### Schema Design
- Always include `tenantId` with index for multi-tenant tables
- Use `@@map("snake_case")` for table/column names
- Include `createdAt`, `updatedAt`, `deletedAt` on all entities
- Use `@default(uuid())` for primary keys
- Add `version` field for optimistic concurrency

### Soft Deletes
- Never hard-delete user data
- Use `deletedAt` timestamp (null = active)
- Filter `deletedAt: null` in all queries
- Entity `.delete()` method sets `deletedAt` + archives

### Migrations
- One migration per feature/change
- Never modify existing migrations
- Test migration on a fresh database
- Include rollback strategy for production

## Repository Pattern

```typescript
// Interface in domain layer
interface IRepository<T> {
  findById(id: string): Promise<T | null>;
  findByTenant(tenantId: string, options?): Promise<T[]>;
  save(entity: T, tx?: unknown): Promise<T>;
  delete(id: string): Promise<void>;
}

// Implementation in infrastructure layer
class PrismaRepository implements IRepository {
  // Uses upsert for save (handles both create and update)
  // toDomain() maps DB record → domain entity
  // toPersistence() maps domain entity → DB record
}
```

## Transaction Pattern

All mutations use Unit of Work:
```typescript
const saved = await unitOfWork.execute(async (tx) => {
  const result = await repository.save(entity, tx);
  return {
    result,
    auditEntries: [],    // Audit log within same transaction
    outboxEntries: [],   // Outbox events within same transaction
  };
});
```
