# Domain-Driven Design Patterns

## Entity Pattern

```typescript
class Entity {
  private constructor(private readonly props: EntityProps) {}

  // Getters — expose read-only access to properties
  get id(): string { return this.props.id; }

  // Static factory — create new entity with validation
  static create(input: CreateInput): Entity {
    // Validate business rules
    // Return new instance with generated ID and defaults
  }

  // Reconstitute from persistence — no validation needed
  static fromPersistence(props: EntityProps): Entity {
    return new Entity(props);
  }

  // Immutable mutation — returns new instance
  update(input: UpdateInput): Entity {
    return new Entity({ ...this.props, ...changes, version: this.props.version + 1 });
  }

  // Serialize for storage
  toPersistence(): EntityProps {
    return { ...this.props };
  }
}
```

## Key Rules

1. **Private constructor** — Force use of `create()` or `fromPersistence()`
2. **Immutable mutations** — `update()` returns a NEW instance, never modifies `this`
3. **Domain validation** — Business rules enforced in `create()` and mutation methods
4. **No infrastructure imports** — Domain entities are pure TypeScript
5. **Version tracking** — Every mutation increments version for optimistic concurrency

## Value Objects

Immutable objects identified by their attributes (not by ID):
- `Money` (amount + currency)
- `Email` (validated email string)
- `Address` (street, city, zip, country)

## Aggregate Root

An entity that owns other entities and enforces consistency boundaries:
- All access to child entities goes through the aggregate root
- Transactions should not span multiple aggregates
- Raises domain events for cross-aggregate communication

## Repository Interface

Defined in the domain layer, implemented in infrastructure:
- `findById()` — Returns domain entity (not DB record)
- `save()` — Persists domain entity (upsert pattern)
- Uses `toDomain()` / `toPersistence()` mappers

## Python Pragmatic DDD

Python codebases use Pydantic `BaseModel` as domain entities. This is a valid, pragmatic approach:

```python
class WorkflowConfig(BaseModel):
    id: str
    name: str
    stages: list[StageConfig] = Field(default_factory=list)
    version: int = 1

    def add_stage(self, stage: StageConfig) -> None:
        self.stages.append(stage)
        self.version += 1
```

**Key differences from TypeScript DDD:**
- **Mutable models** — mutations modify `self` instead of returning new instances
- **No private constructor** — Pydantic handles construction and validation
- **`model_dump()` / `model_validate()`** — replaces `toPersistence()` / `fromPersistence()`
- **`*Store` classes** — replace repository + UoW pattern for simpler persistence needs

Both patterns are valid. Detect the project language and apply the matching convention.
