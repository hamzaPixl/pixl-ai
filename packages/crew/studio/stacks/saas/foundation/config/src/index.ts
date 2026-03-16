import { z } from 'zod';

export const EnvironmentSchema = z.enum(['development', 'staging', 'production', 'test']);
export type Environment = z.infer<typeof EnvironmentSchema>;

export const BaseConfigSchema = z.object({
  env: EnvironmentSchema.default('development'),
  nodeEnv: z.string().default('development'),
  serviceName: z.string().min(1),
  serviceVersion: z.string().default('0.0.0'),
  port: z.coerce.number().int().positive().default(3000),
  host: z.string().default('0.0.0.0'),
  logLevel: z.enum(['trace', 'debug', 'info', 'warn', 'error', 'fatal']).default('info'),
});
export type BaseConfig = z.infer<typeof BaseConfigSchema>;

export const DatabaseConfigSchema = z.object({
  url: z.string().url(),
  poolMin: z.coerce.number().int().nonnegative().default(2),
  poolMax: z.coerce.number().int().positive().default(10),
  ssl: z.coerce.boolean().default(false),
});
export type DatabaseConfig = z.infer<typeof DatabaseConfigSchema>;

export const RedisConfigSchema = z.object({
  url: z.string().url(),
  maxRetries: z.coerce.number().int().nonnegative().default(3),
  retryDelay: z.coerce.number().int().positive().default(1000),
});
export type RedisConfig = z.infer<typeof RedisConfigSchema>;

export const NatsConfigSchema = z.object({
  url: z.string(),
  maxReconnectAttempts: z.coerce.number().int().nonnegative().default(10),
  reconnectTimeWait: z.coerce.number().int().positive().default(2000),
});
export type NatsConfig = z.infer<typeof NatsConfigSchema>;

export const JwtConfigSchema = z.object({
  secret: z.string().min(32),
  expiresIn: z.string().default('1h'),
  refreshExpiresIn: z.string().default('7d'),
  issuer: z.string().optional(),
  audience: z.string().optional(),
});
export type JwtConfig = z.infer<typeof JwtConfigSchema>;

export const CorsConfigSchema = z.object({
  origins: z.array(z.string()).default(['*']),
  methods: z.array(z.string()).default(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']),
  allowedHeaders: z
    .array(z.string())
    .default(['Content-Type', 'Authorization', 'X-Tenant-ID', 'X-Correlation-ID']),
  credentials: z.boolean().default(true),
  maxAge: z.number().default(86400),
});
export type CorsConfig = z.infer<typeof CorsConfigSchema>;

export const RateLimitConfigSchema = z.object({
  enabled: z.boolean().default(true),
  windowMs: z.number().default(60000),
  max: z.number().default(100),
});
export type RateLimitConfig = z.infer<typeof RateLimitConfigSchema>;

export const OtelConfigSchema = z.object({
  enabled: z.boolean().default(true),
  endpoint: z.string().url().optional(),
  serviceName: z.string(),
  serviceVersion: z.string().default('0.0.0'),
  environment: EnvironmentSchema.default('development'),
});
export type OtelConfig = z.infer<typeof OtelConfigSchema>;

export function loadConfig<T extends z.ZodTypeAny>(
  schema: T,
  env: Record<string, string | undefined> = process.env,
): z.infer<T> {
  const result = schema.safeParse(env);

  if (!result.success) {
    const errors = result.error.errors
      .map((e) => `  - ${e.path.join('.')}: ${e.message}`)
      .join('\n');
    throw new Error(`Configuration validation failed:\n${errors}`);
  }

  return result.data;
}

/**
 * @deprecated Use createConfigLoader from composition instead
 */
export function createSimpleConfigLoader<T extends z.ZodRawShape>(
  schema: z.ZodObject<T>,
  envMapping: Record<keyof T, string>,
) {
  return (env: Record<string, string | undefined> = process.env): z.infer<z.ZodObject<T>> => {
    const mapped: Record<string, string | undefined> = {};

    for (const [key, envKey] of Object.entries(envMapping)) {
      const value = env[envKey as string];
      if (value !== undefined) {
        mapped[key] = value;
      }
    }

    return loadConfig(schema, mapped);
  };
}

export function requireEnv(
  key: string,
  env: Record<string, string | undefined> = process.env,
): string {
  const value = env[key];
  if (value === undefined || value === '') {
    throw new Error(`Required environment variable ${key} is not set`);
  }
  return value;
}

export function getEnv(
  key: string,
  defaultValue: string,
  env: Record<string, string | undefined> = process.env,
): string {
  return env[key] ?? defaultValue;
}

export function isProduction(env: Record<string, string | undefined> = process.env): boolean {
  return env['NODE_ENV'] === 'production' || env['ENV'] === 'production';
}

export function isDevelopment(env: Record<string, string | undefined> = process.env): boolean {
  return env['NODE_ENV'] === 'development' || env['ENV'] === 'development';
}

export function isTest(env: Record<string, string | undefined> = process.env): boolean {
  return env['NODE_ENV'] === 'test' || env['ENV'] === 'test';
}

// ============================================================================
// Feature-Specific Config Schemas
// These are common SaaS feature configurations used across services
// ============================================================================

export const OutboxConfigSchema = z.object({
  enabled: z.coerce.boolean().default(true),
  pollIntervalMs: z.coerce.number().int().positive().default(1000),
  batchSize: z.coerce.number().int().positive().default(100),
  maxRetries: z.coerce.number().int().nonnegative().default(5),
  retryDelayMs: z.coerce.number().int().positive().default(1000),
});
export type OutboxConfig = z.infer<typeof OutboxConfigSchema>;

export const AuditConfigSchema = z.object({
  enabled: z.coerce.boolean().default(true),
  retentionDays: z.coerce.number().int().positive().default(90),
});
export type AuditConfig = z.infer<typeof AuditConfigSchema>;

export const JobsConfigSchema = z.object({
  enabled: z.coerce.boolean().default(true),
  defaultAttempts: z.coerce.number().int().positive().default(3),
  defaultBackoff: z.coerce.number().int().positive().default(1000),
  stalledInterval: z.coerce.number().int().positive().default(30000),
});
export type JobsConfig = z.infer<typeof JobsConfigSchema>;

export const RealtimeConfigSchema = z.object({
  enabled: z.coerce.boolean().default(true),
  pingIntervalMs: z.coerce.number().int().positive().default(30000),
  maxConnectionsPerTenant: z.coerce.number().int().positive().default(1000),
});
export type RealtimeConfig = z.infer<typeof RealtimeConfigSchema>;

export const NotificationsConfigSchema = z.object({
  enabled: z.coerce.boolean().default(true),
  emailProvider: z.enum(['console', 'smtp', 'sendgrid', 'ses']).default('console'),
  smtpHost: z.string().optional(),
  smtpPort: z.coerce.number().int().positive().optional(),
  smtpUser: z.string().optional(),
  smtpPass: z.string().optional(),
  fromAddress: z.string().email().default('noreply@example.com'),
});
export type NotificationsConfig = z.infer<typeof NotificationsConfigSchema>;

// ============================================================================
// Config Composition
// ============================================================================

export {
  FOUNDATION_ENV_MAPPING,
  composeConfigSchema,
  deepMergeConfig,
  parseEnvToConfig,
  createConfigLoader,
  type FoundationEnvMappingKey,
  type ConfigCompositionOptions,
  type ConfigLoaderOptions,
  type ConfigLoader,
} from './composition';
