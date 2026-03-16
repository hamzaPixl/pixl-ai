import Fastify, {
  type FastifyInstance,
  type FastifyServerOptions,
  type FastifyBaseLogger,
} from 'fastify';
import type { ILogger, Logger } from '@saas-studio/logger';
import { createLogger } from '@saas-studio/logger';
import { registerJwtPlugin, type JwtConfig } from '@saas-studio/identity';
import {
  createDefaultResolver,
  registerTenantHook,
  type TenantResolver,
} from '@saas-studio/tenancy';
import { registerObservabilityHooks, type AppMetrics } from '@saas-studio/observability';
import {
  registerCors,
  registerHelmet,
  registerRateLimit,
  registerSensible,
  registerSwagger,
  registerHealthChecks,
  type CorsOptions,
  type RateLimitOptions,
  type SwaggerOptions,
  type HealthCheckOptions,
} from '../plugins';
import {
  registerCorrelationId,
  registerRequestLogging,
  registerGracefulShutdown,
} from '../middleware';
import { registerErrorHandler, registerNotFoundHandler } from '../error-handling';

export interface ApiFactoryConfig {
  name: string;
  version?: string;
  port?: number;
  host?: string;
  logLevel?: 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  logPretty?: boolean;
  jwt: JwtConfig;
  cors?: CorsOptions;
  rateLimit?: RateLimitOptions | false;
  helmet?: boolean;
  tenantResolver?: TenantResolver;
  tenantRequired?: boolean;
  baseDomain?: string;
  swagger?: SwaggerOptions | false;
  healthChecks?: HealthCheckOptions;
  metrics?: AppMetrics;
  fastifyOptions?: FastifyServerOptions;
  trustProxy?: boolean;
}

export interface ApiFactory {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  app: FastifyInstance<any, any, any, any, any>;
  logger: Logger;
  start: () => Promise<void>;
  stop: () => Promise<void>;
}

export async function createApiFactory(config: ApiFactoryConfig): Promise<ApiFactory> {
  const logger = createLogger({
    serviceName: config.name,
    serviceVersion: config.version ?? '0.0.0',
    level: config.logLevel ?? 'info',
    pretty: config.logPretty ?? process.env['NODE_ENV'] !== 'production',
  });

  const app = Fastify({
    logger: logger.getPino(),
    trustProxy: config.trustProxy ?? true,
    ...config.fastifyOptions,
  });

  await registerSensible(app);

  if (config.helmet !== false) {
    await registerHelmet(app);
  }

  if (config.cors) {
    await registerCors(app, config.cors);
  }

  if (config.rateLimit !== false && config.rateLimit) {
    await registerRateLimit(app, config.rateLimit);
  }

  await registerJwtPlugin(app, config.jwt);

  registerCorrelationId(app);
  registerRequestLogging(app, logger);

  const tenantResolver = config.tenantResolver ?? createDefaultResolver(config.baseDomain);
  registerTenantHook(app, {
    resolver: tenantResolver,
    required: config.tenantRequired ?? false,
  });

  registerObservabilityHooks(app, {
    logger,
    metrics: config.metrics,
  });

  registerHealthChecks(app, config.healthChecks);

  if (config.swagger !== false && config.swagger) {
    await registerSwagger(app, config.swagger);
  }

  registerErrorHandler(app, { logger });
  registerNotFoundHandler(app);

  registerGracefulShutdown(app, logger);

  const start = async (): Promise<void> => {
    const port = config.port ?? 3000;
    const host = config.host ?? '0.0.0.0';

    await app.listen({ port, host });
    logger.info('Server started', { port, host, name: config.name });
  };

  const stop = async (): Promise<void> => {
    await app.close();
    logger.info('Server stopped');
  };

  return { app, logger, start, stop };
}

export async function createMinimalApiFactory(
  config: Pick<
    ApiFactoryConfig,
    'name' | 'version' | 'port' | 'host' | 'logLevel' | 'logPretty' | 'healthChecks'
  >,
): Promise<ApiFactory> {
  const logger = createLogger({
    serviceName: config.name,
    serviceVersion: config.version ?? '0.0.0',
    level: config.logLevel ?? 'info',
    pretty: config.logPretty ?? process.env['NODE_ENV'] !== 'production',
  });

  const app = Fastify({
    logger: logger.getPino(),
  });

  await registerSensible(app);
  registerCorrelationId(app);
  registerHealthChecks(app, config.healthChecks);
  registerErrorHandler(app, { logger });

  const start = async (): Promise<void> => {
    const port = config.port ?? 3000;
    const host = config.host ?? '0.0.0.0';
    await app.listen({ port, host });
    logger.info('Server started', { port, host });
  };

  const stop = async (): Promise<void> => {
    await app.close();
  };

  return { app, logger, start, stop };
}
