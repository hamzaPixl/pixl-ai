# Content Versioning Patterns

## Strategy: Copy-on-Write

The foundation uses copy-on-write versioning via `VersionedAggregateRoot`:

- Each publish creates an immutable version snapshot
- Drafts are mutable until published
- Version history is stored alongside the entity
- Supports draft → published → archived lifecycle

## Entity States

```
draft → published → archived
  ↑        ↓
  └────────┘  (unpublish)
```

## Usage

Extend `VersionedAggregateRoot` from `@saas-studio/domain`:

```typescript
class Article extends VersionedAggregateRoot<ArticleProps> {
  protected getSnapshotData() {
    return { title: this.props.title, body: this.props.body };
  }

  publish(by: string): Article {
    const props = this.doPublish(by);
    return new Article(props);
  }
}
```

## Database Schema

Add to your Prisma model:

```prisma
status           String   @default("draft")
contentVersion   Int      @default(0) @map("content_version")
publishedVersion Int?     @map("published_version")
publishedAt      DateTime? @map("published_at")
```

## Alternatives

- **Event-sourced versioning**: Store every change as an event. Better audit trail but higher complexity. Use for compliance-heavy domains.
- **Temporal tables**: Database-level versioning (PostgreSQL temporal). Best for simple audit needs without application-level control.
