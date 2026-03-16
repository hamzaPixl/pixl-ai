import { withSpan, addSpanAttributes, SpanKind } from '../tracing';
import type { AppMetrics } from '../metrics';
import type { ILogger } from '@saas-studio/logger';

export interface PrismaQueryEvent {
  timestamp: Date;
  query: string;
  params: string;
  duration: number;
  target: string;
}

export function createPrismaMiddleware(options: {
  logger?: ILogger;
  metrics?: AppMetrics;
  slowQueryThreshold?: number;
}) {
  const { logger, metrics, slowQueryThreshold = 1000 } = options;

  return async (
    params: {
      model?: string;
      action: string;
      args: unknown;
      dataPath: string[];
      runInTransaction: boolean;
    },
    next: (params: unknown) => Promise<unknown>,
  ) => {
    const startTime = Date.now();
    const model = params.model ?? 'unknown';
    const action = params.action;

    try {
      const result = await withSpan(
        `prisma.${model}.${action}`,
        async (span) => {
          span.setAttributes({
            'db.system': 'postgresql',
            'db.operation': action,
            'db.sql.table': model,
          });

          return next(params);
        },
        { kind: SpanKind.CLIENT },
      );

      const duration = Date.now() - startTime;

      metrics?.dbQueryDuration.record(duration, {
        model,
        operation: action,
      });

      if (duration > slowQueryThreshold && logger) {
        logger.warn('Slow database query detected', {
          model,
          action,
          duration,
          threshold: slowQueryThreshold,
        });
      }

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;

      metrics?.dbQueryDuration.record(duration, {
        model,
        operation: action,
        error: 'true',
      });

      addSpanAttributes({
        'db.error': 'true',
        'db.error.message': error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  };
}

export function logPrismaQuery(logger: ILogger, event: PrismaQueryEvent): void {
  logger.debug('Database query executed', {
    query: event.query,
    params: event.params,
    duration: event.duration,
    target: event.target,
  });
}
