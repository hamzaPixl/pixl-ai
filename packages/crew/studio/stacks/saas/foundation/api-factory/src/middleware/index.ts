import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { randomUUID } from 'node:crypto';
import type { ILogger } from '@saas-studio/logger';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFastifyInstance = FastifyInstance<any, any, any, any, any>;

export function registerCorrelationId(fastify: AnyFastifyInstance): void {
  fastify.addHook('onRequest', async (request: FastifyRequest, reply: FastifyReply) => {
    const correlationId = (request.headers['x-correlation-id'] as string) ?? randomUUID();
    const requestId = (request.headers['x-request-id'] as string) ?? randomUUID();

    // Store on request for later use
    (request as FastifyRequest & { correlationId: string }).correlationId = correlationId;
    (request as FastifyRequest & { requestId: string }).requestId = requestId;

    reply.header('x-correlation-id', correlationId);
    reply.header('x-request-id', requestId);
  });
}

export function registerRequestLogging(
  fastify: AnyFastifyInstance,
  logger: ILogger,
  options: { ignorePaths?: string[] } = {},
): void {
  const { ignorePaths = ['/health', '/ready', '/docs'] } = options;

  fastify.addHook('onRequest', async (request: FastifyRequest) => {
    if (ignorePaths.some((path) => request.url.startsWith(path))) {
      return;
    }

    (request as FastifyRequest & { startTime: number }).startTime = Date.now();

    logger.info('Incoming request', {
      method: request.method,
      path: request.url,
      correlationId: (request as FastifyRequest & { correlationId?: string }).correlationId,
      tenantId: request.headers['x-tenant-id'],
      userAgent: request.headers['user-agent'],
    });
  });

  fastify.addHook('onResponse', async (request: FastifyRequest, reply: FastifyReply) => {
    if (ignorePaths.some((path) => request.url.startsWith(path))) {
      return;
    }

    const startTime = (request as FastifyRequest & { startTime?: number }).startTime;
    const duration = startTime ? Date.now() - startTime : 0;

    const logData = {
      method: request.method,
      path: request.url,
      statusCode: reply.statusCode,
      duration,
      correlationId: (request as FastifyRequest & { correlationId?: string }).correlationId,
    };

    if (reply.statusCode >= 500) {
      logger.error('Request completed with error', logData);
    } else if (reply.statusCode >= 400) {
      logger.warn('Request completed with client error', logData);
    } else {
      logger.info('Request completed', logData);
    }
  });
}

export function registerGracefulShutdown(
  fastify: AnyFastifyInstance,
  logger: ILogger,
  options: { timeout?: number; signals?: string[] } = {},
): void {
  const { timeout = 30000, signals = ['SIGTERM', 'SIGINT'] } = options;

  const shutdown = async (signal: string): Promise<void> => {
    logger.info('Received shutdown signal', { signal });

    const forceShutdown = setTimeout(() => {
      logger.error('Forced shutdown due to timeout');
      process.exit(1);
    }, timeout);

    try {
      await fastify.close();
      logger.info('Server closed gracefully');
      clearTimeout(forceShutdown);
      process.exit(0);
    } catch (error) {
      logger.error('Error during shutdown', {
        error: error instanceof Error ? error.message : 'Unknown',
      });
      clearTimeout(forceShutdown);
      process.exit(1);
    }
  };

  for (const signal of signals) {
    process.on(signal, () => shutdown(signal));
  }
}

declare module 'fastify' {
  interface FastifyRequest {
    correlationId?: string;
    requestId?: string;
    startTime?: number;
  }
}

export {
  validateBody,
  validateQuery,
  validateParams,
  getValidatedBody,
  getValidatedQuery,
  getValidatedParams,
  createValidationHandlers,
} from './validation';
export type { ValidationOptions } from './validation';

export {
  extractPagination,
  getPagination,
  calculateSkip,
  toRepositoryOptions,
  extractPaginationContext,
} from './pagination';
export type {
  PaginationContext,
  PaginationMiddlewareOptions,
  PaginationQuery,
  ExtractPaginationOptions,
} from './pagination';
