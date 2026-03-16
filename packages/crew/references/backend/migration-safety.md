# Migration Safety Patterns

Reference for the `/migration-plan` skill. Safe patterns for database and code migrations.

## The Expand-Migrate-Contract Pattern

The safest approach for non-trivial schema changes:

1. **Expand**: Add new structures alongside old ones (backwards compatible)
2. **Migrate**: Copy/transform data from old to new
3. **Contract**: Remove old structures after verification

This ensures zero-downtime and safe rollback at every step.

## Safe Operations (usually no downtime)

- Adding a new table
- Adding a nullable column
- Adding a column with a default value (Postgres 11+ is instant)
- Adding an index CONCURRENTLY (Postgres)
- Adding a CHECK constraint NOT VALID + later VALIDATE

## Dangerous Operations (require care)

| Operation | Risk | Safe Alternative |
|-----------|------|-----------------|
| Drop column | Data loss | Rename → deprecate → drop after verification |
| Rename column | Breaks queries | Add new → dual-write → migrate → drop old |
| Change column type | Cast failure | Add new column → backfill → swap |
| Add NOT NULL | Fails on existing NULLs | Add CHECK NOT VALID → backfill → VALIDATE → set NOT NULL |
| Drop table | Data loss | Rename to `_deprecated_` → wait → drop |
| Large table ALTER | Locks | Use `pg_repack` or online DDL tools |

## Batch Processing for Data Migrations

Never update all rows in one transaction:

```sql
-- Bad: locks entire table
UPDATE large_table SET new_col = transform(old_col);

-- Good: batch processing
DO $$
DECLARE
  batch_size INT := 1000;
  rows_updated INT;
BEGIN
  LOOP
    UPDATE large_table
    SET new_col = transform(old_col)
    WHERE new_col IS NULL
    LIMIT batch_size;

    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    EXIT WHEN rows_updated = 0;

    PERFORM pg_sleep(0.1); -- breathing room
    COMMIT;
  END LOOP;
END $$;
```

## Rollback Strategies

| Scenario | Strategy |
|----------|----------|
| New column added | Drop column (safe, no data in it yet) |
| Data backfilled | Reverse transformation or restore from backup |
| Old column dropped | Restore from backup (point of no return) |
| Index added | Drop index (safe) |
| Constraint added | Drop constraint (safe) |

## Pre-flight Checklist

- [ ] Full database backup exists and is verified
- [ ] Migration tested on staging with production-like data
- [ ] Rollback script written and tested
- [ ] Estimated migration time calculated (row count × per-row time)
- [ ] Lock time estimated for DDL operations
- [ ] Monitoring dashboards ready (error rates, latency, connection pool)
- [ ] Communication plan (maintenance window or silent deploy)
- [ ] All dependent services identified and their deploy order planned

## Prisma-Specific Safety

- Always review generated SQL: `npx prisma migrate diff`
- Use `prisma migrate deploy` (not `dev`) in production
- For large data migrations, use raw SQL in a separate script
- Watch for implicit index creation on `@unique` and `@relation`

## SQLAlchemy/Alembic-Specific Safety

- Always generate migration, then review before applying
- Use `batch_alter_table` for SQLite (no ALTER support)
- Set `compare_type=True` in env.py for type change detection
- Use `op.execute()` for raw SQL in complex migrations
