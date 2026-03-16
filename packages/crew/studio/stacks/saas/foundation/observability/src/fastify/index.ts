import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import type { ILogger } from '@saas-studio/logger';
import { getCurrentTraceId, addSpanAttributes } from '../tracing';
import { type AppMetrics } from '../metrics';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFastifyInstance = FastifyInstance<any, any, any, any, any>;

export interface ObservabilityPluginOptions {
  logger: ILogger;
  metrics?: AppMetrics;
  ignorePaths?: string[];
}

interface RequestTiming {
  startTime: number;
}

export function registerObservabilityHooks(
  fastify: AnyFastifyInstance,
  options: ObservabilityPluginOptions,
): void {
  const { logger, metrics, ignorePaths = ['/health', '/ready', '/metrics'] } = options;

  fastify.decorateRequest('timing', null);

  fastify.addHook('onRequest', async (request: FastifyRequest) => {
    const timing: RequestTiming = { startTime: Date.now() };
    (request as FastifyRequest & { timing: RequestTiming }).timing = timing;

    if (ignorePaths.includes(request.url)) {
      return;
    }

    metrics?.httpActiveRequests.add(1, {
      method: request.method,
      path: request.routeOptions?.url ?? request.url,
    });

    addSpanAttributes({
      'http.method': request.method,
      'http.url': request.url,
      'http.route': request.routeOptions?.url ?? request.url,
      'tenant.id': (request.headers['x-tenant-id'] as string) ?? 'unknown',
    });
  });

  fastify.addHook('onResponse', async (request: FastifyRequest, reply: FastifyReply) => {
    const timing = (request as FastifyRequest & { timing?: RequestTiming }).timing;
    const duration = timing ? Date.now() - timing.startTime : 0;

    if (ignorePaths.includes(request.url)) {
      return;
    }

    const path = request.routeOptions?.url ?? request.url;
    const method = request.method;
    const statusCode = reply.statusCode;

    metrics?.httpActiveRequests.add(-1, { method, path });
    metrics?.httpRequestsTotal.add(1, {
      method,
      path,
      status_code: statusCode.toString(),
    });
    metrics?.httpRequestDuration.record(duration, {
      method,
      path,
      status_code: statusCode.toString(),
    });

    const logData = {
      method,
      path,
      statusCode,
      duration,
      traceId: getCurrentTraceId(),
      correlationId: request.headers['x-correlation-id'],
      tenantId: request.headers['x-tenant-id'],
      userAgent: request.headers['user-agent'],
    };

    if (statusCode >= 500) {
      logger.error('Request completed with error', logData);
    } else if (statusCode >= 400) {
      logger.warn('Request completed with client error', logData);
    } else {
      logger.info('Request completed', logData);
    }
  });

  fastify.addHook(
    'onError',
    async (request: FastifyRequest, _reply: FastifyReply, error: Error) => {
      logger.error('Request error', {
        method: request.method,
        path: request.url,
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack,
        },
        traceId: getCurrentTraceId(),
        correlationId: request.headers['x-correlation-id'],
        tenantId: request.headers['x-tenant-id'],
      });
    },
  );
}

export async function healthHandler(): Promise<{ status: string; timestamp: string }> {
  return {
    status: 'ok',
    timestamp: new Date().toISOString(),
  };
}

export type ReadinessChecker = () => Promise<boolean>;

export function createReadinessHandler(checkers: Record<string, ReadinessChecker>) {
  return async (): Promise<{
    status: string;
    checks: Record<string, { status: string }>;
    timestamp: string;
  }> => {
    const results: Record<string, { status: string }> = {};
    let allReady = true;

    for (const [name, checker] of Object.entries(checkers)) {
      try {
        const ready = await checker();
        results[name] = { status: ready ? 'ok' : 'not_ready' };
        if (!ready) allReady = false;
      } catch {
        results[name] = { status: 'error' };
        allReady = false;
      }
    }

    return {
      status: allReady ? 'ok' : 'not_ready',
      checks: results,
      timestamp: new Date().toISOString(),
    };
  };
}
