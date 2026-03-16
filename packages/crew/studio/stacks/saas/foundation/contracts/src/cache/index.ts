/**
 * Cache utilities with SCAN-based invalidation for Redis-compatible stores.
 *
 * Uses SCAN instead of KEYS to avoid blocking the Redis event loop on large datasets.
 * Pattern-based invalidation lets you clear all cache entries for a tenant or entity type.
 */

export interface CacheStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, ttlSeconds?: number): Promise<void>;
  del(key: string): Promise<void>;
  scan(
    cursor: string,
    pattern: string,
    count?: number,
  ): Promise<[string, string[]]>;
}

/**
 * Build a namespaced cache key.
 *
 * Format: `{prefix}:{tenantId}:{entity}:{id}`
 * Enables pattern-based SCAN invalidation (e.g., `app:tenant-123:*`).
 */
export function cacheKey(parts: {
  prefix: string;
  tenantId: string;
  entity: string;
  id?: string;
}): string {
  const base = `${parts.prefix}:${parts.tenantId}:${parts.entity}`;
  return parts.id ? `${base}:${parts.id}` : base;
}

/**
 * Invalidate all cache entries matching a pattern using SCAN (non-blocking).
 *
 * Unlike KEYS, SCAN iterates incrementally and won't block Redis on large datasets.
 * Typical patterns:
 * - `app:tenant-123:*` — all entries for a tenant
 * - `app:*:articles:*` — all article entries across tenants
 */
export async function invalidateByPattern(
  store: CacheStore,
  pattern: string,
  batchSize: number = 100,
): Promise<number> {
  let cursor = "0";
  let deleted = 0;

  do {
    const [nextCursor, keys] = await store.scan(cursor, pattern, batchSize);
    cursor = nextCursor;

    for (const key of keys) {
      await store.del(key);
      deleted++;
    }
  } while (cursor !== "0");

  return deleted;
}

/**
 * Get-or-set cache helper with TTL.
 */
export async function cached<T>(
  store: CacheStore,
  key: string,
  factory: () => Promise<T>,
  ttlSeconds: number = 300,
): Promise<T> {
  const existing = await store.get(key);
  if (existing !== null) {
    return JSON.parse(existing) as T;
  }

  const value = await factory();
  await store.set(key, JSON.stringify(value), ttlSeconds);
  return value;
}
