/**
 * API Key authentication module.
 *
 * Supports X-API-Key header authentication for public/service-to-service access.
 * Keys are stored as SHA-256 hashes — never store raw keys.
 */

import { createHash, randomBytes } from "node:crypto";
import type { FastifyRequest, FastifyReply } from "fastify";
import { createServiceActor, runWithContextAsync } from "../actor";

export interface ApiKeyConfig {
  headerName?: string;
  prefix?: string;
}

const DEFAULT_CONFIG: Required<ApiKeyConfig> = {
  headerName: "x-api-key",
  prefix: "pk_",
};

/**
 * Generate a new API key pair: raw key (give to client) + hash (store in DB).
 */
export function generateApiKey(prefix?: string): {
  rawKey: string;
  keyHash: string;
} {
  const pfx = prefix ?? DEFAULT_CONFIG.prefix;
  const rawKey = `${pfx}${randomBytes(32).toString("hex")}`;
  const keyHash = hashApiKey(rawKey);
  return { rawKey, keyHash };
}

/**
 * Hash an API key for storage. Uses SHA-256.
 */
export function hashApiKey(rawKey: string): string {
  return createHash("sha256").update(rawKey).digest("hex");
}

/**
 * Verify a raw API key against a stored hash.
 */
export function verifyApiKey(rawKey: string, storedHash: string): boolean {
  const hash = hashApiKey(rawKey);
  // Constant-time comparison to prevent timing attacks
  if (hash.length !== storedHash.length) return false;
  let result = 0;
  for (let i = 0; i < hash.length; i++) {
    result |= hash.charCodeAt(i) ^ storedHash.charCodeAt(i);
  }
  return result === 0;
}

export interface ApiKeyRecord {
  id: string;
  keyHash: string;
  tenantId: string;
  name: string;
  scopes: string[];
  expiresAt: Date | null;
}

export type ApiKeyLookup = (keyHash: string) => Promise<ApiKeyRecord | null>;

/**
 * Create a Fastify preHandler that authenticates via API key.
 *
 * Usage:
 * ```typescript
 * fastify.get('/api/public', {
 *   preHandler: [apiKeyGuard(lookupFn)],
 * }, handler);
 * ```
 */
export function apiKeyGuard(lookup: ApiKeyLookup, config?: ApiKeyConfig) {
  const { headerName } = { ...DEFAULT_CONFIG, ...config };

  return async (request: FastifyRequest, reply: FastifyReply) => {
    const rawKey = request.headers[headerName] as string | undefined;

    if (!rawKey) {
      reply
        .status(401)
        .send({ error: "API key required", code: "API_KEY_MISSING" });
      return;
    }

    const keyHash = hashApiKey(rawKey);
    const record = await lookup(keyHash);

    if (!record) {
      reply
        .status(401)
        .send({ error: "Invalid API key", code: "API_KEY_INVALID" });
      return;
    }

    if (record.expiresAt && record.expiresAt < new Date()) {
      reply
        .status(401)
        .send({ error: "API key expired", code: "API_KEY_EXPIRED" });
      return;
    }

    // Set up actor context for the request (service actor with tenant scope)
    const actor = createServiceActor(record.tenantId, `apikey:${record.id}`);
    await runWithContextAsync(
      {
        actor,
        tenantId: record.tenantId,
        correlationId: request.id,
      },
      async () => {
        // Attach key metadata to request for downstream use
        (request as unknown as Record<string, unknown>).apiKeyRecord = record;
      },
    );
  };
}
