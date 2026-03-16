import { z, type ZodSchema, type ZodObject, type ZodRawShape } from 'zod';
import {
  BaseConfigSchema,
  DatabaseConfigSchema,
  RedisConfigSchema,
  NatsConfigSchema,
  JwtConfigSchema,
  CorsConfigSchema,
  RateLimitConfigSchema,
  OtelConfigSchema,
  OutboxConfigSchema,
  AuditConfigSchema,
  JobsConfigSchema,
  RealtimeConfigSchema,
  NotificationsConfigSchema,
} from './index';

/**
 * Standard environment variable mapping for all foundation config schemas.
 * Maps dot-notation config paths to their corresponding environment variable names.
 */
export const FOUNDATION_ENV_MAPPING = {
  // Base config
  'base.env': 'ENV',
  'base.nodeEnv': 'NODE_ENV',
  'base.serviceName': 'SERVICE_NAME',
  'base.serviceVersion': 'SERVICE_VERSION',
  'base.port': 'PORT',
  'base.host': 'HOST',
  'base.logLevel': 'LOG_LEVEL',

  // Database config
  'database.url': 'DATABASE_URL',
  'database.poolMin': 'DATABASE_POOL_MIN',
  'database.poolMax': 'DATABASE_POOL_MAX',
  'database.ssl': 'DATABASE_SSL',

  // Redis config
  'redis.url': 'REDIS_URL',
  'redis.maxRetries': 'REDIS_MAX_RETRIES',
  'redis.retryDelay': 'REDIS_RETRY_DELAY',

  // NATS config
  'nats.url': 'NATS_URL',
  'nats.maxReconnectAttempts': 'NATS_MAX_RECONNECT_ATTEMPTS',
  'nats.reconnectTimeWait': 'NATS_RECONNECT_TIME_WAIT',

  // JWT config
  'jwt.secret': 'JWT_SECRET',
  'jwt.expiresIn': 'JWT_EXPIRES_IN',
  'jwt.refreshExpiresIn': 'JWT_REFRESH_EXPIRES_IN',
  'jwt.issuer': 'JWT_ISSUER',
  'jwt.audience': 'JWT_AUDIENCE',

  // CORS config
  'cors.origins': 'CORS_ORIGINS',
  'cors.credentials': 'CORS_CREDENTIALS',

  // Rate limit config
  'rateLimit.enabled': 'RATE_LIMIT_ENABLED',
  'rateLimit.windowMs': 'RATE_LIMIT_WINDOW_MS',
  'rateLimit.max': 'RATE_LIMIT_MAX',

  // OpenTelemetry config
  'otel.enabled': 'OTEL_ENABLED',
  'otel.endpoint': 'OTEL_EXPORTER_OTLP_ENDPOINT',
  'otel.serviceName': 'OTEL_SERVICE_NAME',
  'otel.serviceVersion': 'OTEL_SERVICE_VERSION',

  // Outbox config
  'outbox.enabled': 'OUTBOX_ENABLED',
  'outbox.pollIntervalMs': 'OUTBOX_POLL_INTERVAL_MS',
  'outbox.batchSize': 'OUTBOX_BATCH_SIZE',
  'outbox.maxRetries': 'OUTBOX_MAX_RETRIES',

  // Audit config
  'audit.enabled': 'AUDIT_ENABLED',
  'audit.retentionDays': 'AUDIT_RETENTION_DAYS',

  // Jobs config
  'jobs.enabled': 'JOBS_ENABLED',
  'jobs.defaultAttempts': 'JOBS_DEFAULT_ATTEMPTS',
  'jobs.defaultBackoff': 'JOBS_DEFAULT_BACKOFF',

  // Realtime config
  'realtime.enabled': 'REALTIME_ENABLED',
  'realtime.pingIntervalMs': 'REALTIME_PING_INTERVAL_MS',
  'realtime.maxConnectionsPerTenant': 'REALTIME_MAX_CONNECTIONS_PER_TENANT',

  // Notifications config
  'notifications.enabled': 'NOTIFICATIONS_ENABLED',
  'notifications.emailProvider': 'NOTIFICATIONS_EMAIL_PROVIDER',
  'notifications.smtpHost': 'SMTP_HOST',
  'notifications.smtpPort': 'SMTP_PORT',
  'notifications.smtpUser': 'SMTP_USER',
  'notifications.smtpPass': 'SMTP_PASS',
  'notifications.fromAddress': 'NOTIFICATIONS_FROM_ADDRESS',
} as const;

export type FoundationEnvMappingKey = keyof typeof FOUNDATION_ENV_MAPPING;

/**
 * Options for composing a config schema from foundation schemas.
 */
export interface ConfigCompositionOptions {
  /** Include base config (required for most apps) */
  base?: boolean;
  /** Include database config */
  database?: boolean | 'optional';
  /** Include Redis config */
  redis?: boolean | 'optional';
  /** Include NATS config */
  nats?: boolean | 'optional';
  /** Include JWT config */
  jwt?: boolean | 'optional';
  /** Include CORS config */
  cors?: boolean | 'optional';
  /** Include rate limit config */
  rateLimit?: boolean | 'optional';
  /** Include OpenTelemetry config */
  otel?: boolean | 'optional';
  /** Include outbox config */
  outbox?: boolean | 'optional';
  /** Include audit config */
  audit?: boolean | 'optional';
  /** Include jobs config */
  jobs?: boolean | 'optional';
  /** Include realtime config */
  realtime?: boolean | 'optional';
  /** Include notifications config */
  notifications?: boolean | 'optional';
  /** Additional custom schemas to include */
  extend?: ZodRawShape;
}

type SchemaOption = boolean | 'optional' | undefined;

function addSchema<T extends ZodRawShape>(
  shape: T,
  key: string,
  schema: ZodSchema,
  option: SchemaOption,
): T {
  if (!option) return shape;
  return {
    ...shape,
    [key]: option === 'optional' ? schema.optional() : schema,
  } as T;
}

/**
 * Composes a config schema from foundation schemas based on options.
 * This allows apps to declaratively specify which config sections they need.
 */
export function composeConfigSchema(
  options: ConfigCompositionOptions,
): ZodObject<ZodRawShape> {
  let shape: ZodRawShape = {};

  shape = addSchema(shape, 'base', BaseConfigSchema, options.base);
  shape = addSchema(shape, 'database', DatabaseConfigSchema, options.database);
  shape = addSchema(shape, 'redis', RedisConfigSchema, options.redis);
  shape = addSchema(shape, 'nats', NatsConfigSchema, options.nats);
  shape = addSchema(shape, 'jwt', JwtConfigSchema, options.jwt);
  shape = addSchema(shape, 'cors', CorsConfigSchema, options.cors);
  shape = addSchema(shape, 'rateLimit', RateLimitConfigSchema, options.rateLimit);
  shape = addSchema(shape, 'otel', OtelConfigSchema, options.otel);
  shape = addSchema(shape, 'outbox', OutboxConfigSchema, options.outbox);
  shape = addSchema(shape, 'audit', AuditConfigSchema, options.audit);
  shape = addSchema(shape, 'jobs', JobsConfigSchema, options.jobs);
  shape = addSchema(shape, 'realtime', RealtimeConfigSchema, options.realtime);
  shape = addSchema(shape, 'notifications', NotificationsConfigSchema, options.notifications);

  if (options.extend) {
    shape = { ...shape, ...options.extend };
  }

  return z.object(shape);
}

/**
 * Deep merges two objects, with source values taking precedence.
 * Only merges plain objects; arrays and primitives are replaced.
 */
export function deepMergeConfig<T extends Record<string, unknown>>(
  target: T,
  source: Partial<T>,
): T {
  const result = { ...target };

  for (const key of Object.keys(source) as (keyof T)[]) {
    const sourceValue = source[key];
    const targetValue = target[key];

    if (
      sourceValue !== undefined &&
      typeof sourceValue === 'object' &&
      sourceValue !== null &&
      !Array.isArray(sourceValue) &&
      typeof targetValue === 'object' &&
      targetValue !== null &&
      !Array.isArray(targetValue)
    ) {
      result[key] = deepMergeConfig(
        targetValue as Record<string, unknown>,
        sourceValue as Record<string, unknown>,
      ) as T[keyof T];
    } else if (sourceValue !== undefined) {
      result[key] = sourceValue as T[keyof T];
    }
  }

  return result;
}

/**
 * Parses environment variables into a nested configuration object
 * based on the provided mapping (defaults to FOUNDATION_ENV_MAPPING).
 */
export function parseEnvToConfig(
  env: Record<string, string | undefined>,
  mapping: Record<string, string> = FOUNDATION_ENV_MAPPING,
): Record<string, unknown> {
  const config: Record<string, Record<string, unknown>> = {};

  for (const [path, envKey] of Object.entries(mapping)) {
    const value = env[envKey];
    if (value === undefined) continue;

    const [section, key] = path.split('.');
    if (!section || !key) continue;

    if (!config[section]) {
      config[section] = {};
    }

    // Handle array values (comma-separated)
    if (envKey === 'CORS_ORIGINS') {
      config[section][key] = value.split(',').map((s) => s.trim());
    } else {
      config[section][key] = value;
    }
  }

  return config;
}

/**
 * Options for creating a config loader.
 */
export interface ConfigLoaderOptions<T> {
  /** The Zod schema to validate against. The schema output must be assignable to T. */
  schema: z.ZodType<T, z.ZodTypeDef, unknown>;
  /** Function that returns environment-specific defaults */
  defaults?: (env: Record<string, string | undefined>) => Partial<T>;
  /** Custom env-to-config mapping (defaults to FOUNDATION_ENV_MAPPING) */
  envMapping?: Record<string, string>;
}

/**
 * A config loader instance with load, get, and clear methods.
 */
export interface ConfigLoader<T> {
  /** Loads and validates configuration, caching the result */
  load: (env?: Record<string, string | undefined>) => T;
  /** Returns cached config or throws if not loaded */
  get: () => T;
  /** Clears the cached configuration */
  clear: () => void;
}

/**
 * Creates a config loader with caching, environment-aware defaults,
 * and automatic env-to-config mapping.
 */
export function createConfigLoader<T>(options: ConfigLoaderOptions<T>): ConfigLoader<T> {
  let cached: T | null = null;

  const load = (env: Record<string, string | undefined> = process.env): T => {
    if (cached) {
      return cached;
    }

    const envConfig = parseEnvToConfig(env, options.envMapping);
    const defaults = options.defaults?.(env) ?? ({} as Partial<T>);
    const merged = deepMergeConfig(defaults as Record<string, unknown>, envConfig);

    const result = options.schema.safeParse(merged);
    if (!result.success) {
      const errors = result.error.errors
        .map((e) => `  - ${e.path.join('.')}: ${e.message}`)
        .join('\n');
      throw new Error(`Configuration validation failed:\n${errors}`);
    }

    cached = result.data;
    return cached;
  };

  const get = (): T => {
    if (!cached) {
      throw new Error('Config not loaded. Call load() first.');
    }
    return cached;
  };

  const clear = (): void => {
    cached = null;
  };

  return { load, get, clear };
}
