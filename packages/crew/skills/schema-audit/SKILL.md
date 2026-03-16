---
name: schema-audit
description: "Audit database schemas for redundant indexes, missing foreign keys, naming inconsistencies, N+1 risks, and migration safety. Supports Prisma, SQLAlchemy, raw SQL, and SQLite. Use when asked to review a schema, check database design, find index issues, or audit migrations."
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "<optional: path to schema file or migrations directory>"
---

## Overview

Full database schema audit pipeline: discovery → index audit → constraint audit → naming audit → migration safety → scorecard. Outputs a prioritized report with severity ratings and fix recommendations.

## Required References

Before starting, read `references/backend/schema-audit-checklist.md` for the complete audit checklist and scoring criteria.

## Step 1: Discovery

1. **ORM detection**:
   - Check for `schema.prisma`, `prisma/schema.prisma`, `prisma/` directory (Prisma)
   - Check for `alembic/`, `alembic.ini`, files importing `sqlalchemy` (SQLAlchemy)
   - Check for `*.sql` migration files, `migrations/` directories
   - Check for `*.sqlite`, `*.db` files (SQLite)
2. **Schema inventory**:
   - List all models/tables with their fields and types
   - Map all relationships (1:1, 1:N, M:N)
   - Identify join tables and through models
3. **Migration history**:
   - List all migrations in chronological order
   - Identify pending/unapplied migrations

## Step 2: Index Audit

For each table:

1. **Missing indexes**:
   - Foreign key columns without indexes
   - Columns used in WHERE clauses (grep for query patterns)
   - Columns used in ORDER BY
   - Composite queries needing compound indexes
2. **Redundant indexes**:
   - Indexes that are prefixes of other compound indexes
   - Duplicate indexes on the same column(s)
   - Indexes on boolean columns with low cardinality
3. **Index naming**:
   - Verify consistent naming convention (e.g., `idx_{table}_{columns}`)

## Step 3: Constraint Audit

1. **Missing foreign keys**:
   - Fields ending in `_id` or `Id` without FK constraints
   - Relationships defined in ORM but missing at DB level
2. **Missing NOT NULL**:
   - Required business fields that allow NULL
   - Enum/status fields without defaults
3. **Missing unique constraints**:
   - Natural keys (email, slug, code) without unique indexes
   - Composite uniqueness (tenant_id + name) not enforced
4. **Cascade rules**:
   - ON DELETE behavior for each FK (CASCADE vs SET NULL vs RESTRICT)
   - Orphan risk analysis

## Step 4: Naming Audit

1. **Table naming**:
   - Consistent pluralization (all plural or all singular)
   - Consistent casing (snake_case vs camelCase vs PascalCase)
   - No reserved SQL keywords as names
2. **Column naming**:
   - Consistent ID column naming (`id` vs `{table}_id`)
   - Timestamp columns (`created_at`, `updated_at`) present on all tables
   - Boolean columns prefixed with `is_` or `has_`
3. **Relationship naming**:
   - FK columns match referenced table name (`user_id` → `users`)

## Step 5: N+1 Risk Analysis

1. **Eager loading gaps**:
   - Find query patterns that fetch lists then access relations
   - Prisma: `findMany` without `include` on accessed relations
   - SQLAlchemy: queries without `joinedload`/`selectinload`
2. **Query patterns**:
   - Loops that execute queries (grep for queries inside for/forEach)
   - Count queries that could use `_count` or subqueries

## Step 6: Migration Safety

1. **Dangerous operations**:
   - Column renames (data loss risk)
   - Column type changes (cast failures)
   - NOT NULL additions without defaults
   - Table drops or column drops
   - Large table ALTERs (lock risk)
2. **Missing rollback**:
   - Migrations without corresponding down/rollback
   - Irreversible operations flagged
3. **Data integrity**:
   - Migrations that should backfill data
   - Index creation on large tables (should be CONCURRENTLY)

## Step 7: Scorecard

Output a summary scorecard:

```
## Schema Audit Scorecard

| Category          | Score | Issues |
|-------------------|-------|--------|
| Indexes           | X/10  | N      |
| Constraints       | X/10  | N      |
| Naming            | X/10  | N      |
| N+1 Risks         | X/10  | N      |
| Migration Safety  | X/10  | N      |
| **Overall**       | X/10  | N      |

### Critical Issues (fix immediately)
- ...

### Warnings (fix soon)
- ...

### Suggestions (nice to have)
- ...
```

Rate each finding:
- 🔴 **Critical**: Data loss risk, missing FKs on critical relations, dangerous migrations
- 🟡 **Warning**: Missing indexes on queried columns, naming inconsistencies, N+1 patterns
- 🟢 **Suggestion**: Minor naming tweaks, optional indexes, style preferences
