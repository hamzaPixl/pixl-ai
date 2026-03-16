import type { FastifyInstance } from 'fastify';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFastifyInstance = FastifyInstance<any, any, any, any, any>;

export interface CorsOptions {
  origins: string[];
  methods?: string[];
  allowedHeaders?: string[];
  credentials?: boolean;
  maxAge?: number;
}

export async function registerCors(
  fastify: AnyFastifyInstance,
  options: CorsOptions,
): Promise<void> {
  const cors = await import('@fastify/cors');
  await fastify.register(cors.default, {
    origin: options.origins,
    methods: options.methods ?? ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: options.allowedHeaders ?? [
      'Content-Type',
      'Authorization',
      'X-Tenant-ID',
      'X-Correlation-ID',
      'X-Request-ID',
    ],
    credentials: options.credentials ?? true,
    maxAge: options.maxAge ?? 86400,
  });
}

export interface HelmetOptions {
  contentSecurityPolicy?: boolean;
  crossOriginEmbedderPolicy?: boolean;
}

export async function registerHelmet(
  fastify: AnyFastifyInstance,
  options: HelmetOptions = {},
): Promise<void> {
  const helmet = await import('@fastify/helmet');
  await fastify.register(helmet.default, {
    contentSecurityPolicy: options.contentSecurityPolicy ?? false,
    crossOriginEmbedderPolicy: options.crossOriginEmbedderPolicy ?? false,
  });
}

export interface RateLimitOptions {
  max: number;
  timeWindow?: string | number;
  keyGenerator?: (request: unknown) => string;
}

export async function registerRateLimit(
  fastify: AnyFastifyInstance,
  options: RateLimitOptions,
): Promise<void> {
  const rateLimit = await import('@fastify/rate-limit');
  await fastify.register(rateLimit.default, {
    max: options.max,
    timeWindow: options.timeWindow ?? '1 minute',
    keyGenerator: options.keyGenerator,
  });
}

export async function registerSensible(fastify: AnyFastifyInstance): Promise<void> {
  const sensible = await import('@fastify/sensible');
  await fastify.register(sensible.default);
}

export interface SwaggerOptions {
  title: string;
  description?: string;
  version: string;
  basePath?: string;
  tags?: Array<{ name: string; description: string }>;
}

export async function registerSwagger(
  fastify: AnyFastifyInstance,
  options: SwaggerOptions,
): Promise<void> {
  const swagger = await import('@fastify/swagger');
  const swaggerUi = await import('@fastify/swagger-ui');

  await fastify.register(swagger.default, {
    openapi: {
      info: {
        title: options.title,
        description: options.description,
        version: options.version,
      },
      servers: [{ url: options.basePath ?? '/' }],
      tags: options.tags,
      components: {
        securitySchemes: {
          bearerAuth: {
            type: 'http',
            scheme: 'bearer',
            bearerFormat: 'JWT',
          },
        },
      },
    },
  });

  await fastify.register(swaggerUi.default, {
    routePrefix: '/docs',
  });
}

export interface HealthCheckOptions {
  healthPath?: string;
  readyPath?: string;
  readyChecks?: Record<string, () => Promise<boolean>>;
}

export function registerHealthChecks(
  fastify: AnyFastifyInstance,
  options: HealthCheckOptions = {},
): void {
  const { healthPath = '/health', readyPath = '/ready', readyChecks = {} } = options;

  fastify.get(healthPath, async () => ({
    status: 'ok',
    timestamp: new Date().toISOString(),
  }));

  fastify.get(readyPath, async () => {
    const checks: Record<string, { status: string }> = {};
    let allReady = true;

    for (const [name, check] of Object.entries(readyChecks)) {
      try {
        const ready = await check();
        checks[name] = { status: ready ? 'ok' : 'not_ready' };
        if (!ready) allReady = false;
      } catch {
        checks[name] = { status: 'error' };
        allReady = false;
      }
    }

    return {
      status: allReady ? 'ok' : 'not_ready',
      checks,
      timestamp: new Date().toISOString(),
    };
  });
}
