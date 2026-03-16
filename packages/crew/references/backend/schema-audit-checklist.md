# Schema Audit Checklist

Reference checklist for the `/schema-audit` skill. Each item maps to a step in the audit pipeline.

## Index Checklist

- [ ] All FK columns have indexes
- [ ] Columns in frequent WHERE clauses are indexed
- [ ] Columns in ORDER BY are indexed
- [ ] Compound indexes exist for multi-column queries
- [ ] No redundant indexes (prefixes of existing compound indexes)
- [ ] No duplicate indexes on the same column set
- [ ] No indexes on low-cardinality boolean columns (unless partitioned)
- [ ] Index names follow `idx_{table}_{columns}` convention

## Constraint Checklist

- [ ] All `*_id` / `*Id` columns have FK constraints
- [ ] ORM relationships have corresponding DB-level FKs
- [ ] Required business fields are NOT NULL
- [ ] Enum/status fields have defaults
- [ ] Natural keys (email, slug, code) have UNIQUE constraints
- [ ] Multi-tenant unique constraints include `tenant_id`
- [ ] ON DELETE behavior is explicitly set (not relying on defaults)
- [ ] No orphan risk — cascades or restrict are appropriate

## Naming Checklist

- [ ] Tables use consistent pluralization
- [ ] Tables use consistent casing (snake_case recommended)
- [ ] No SQL reserved keywords as table/column names
- [ ] ID columns use consistent naming (`id` primary, `{table}_id` foreign)
- [ ] All tables have `created_at` and `updated_at` timestamps
- [ ] Boolean columns prefixed with `is_` or `has_`
- [ ] FK columns reference parent table name (`user_id` → `users`)

## N+1 Risk Checklist

- [ ] List queries include necessary relations (Prisma `include`, SQLAlchemy `joinedload`)
- [ ] No queries executed inside loops
- [ ] Aggregations use DB-level COUNT/SUM (not application-level)
- [ ] Batch operations used where applicable

## Migration Safety Checklist

- [ ] Column renames use two-step approach (add new → migrate data → drop old)
- [ ] NOT NULL additions include DEFAULT value
- [ ] Large table index creation uses CONCURRENTLY (Postgres)
- [ ] All migrations have rollback/down counterparts
- [ ] No irreversible operations without explicit documentation
- [ ] Data backfill migrations are separate from schema migrations

## Scoring

| Severity | Criteria |
|----------|----------|
| 🔴 Critical | Data loss risk, missing FKs on critical relations, dangerous migrations without rollback |
| 🟡 Warning | Missing indexes on queried columns, naming inconsistencies, N+1 patterns |
| 🟢 Suggestion | Minor naming tweaks, optional indexes, style preferences |

**Score calculation**: Start at 10, subtract 2 per critical, 1 per warning, 0.5 per suggestion (min 0).
