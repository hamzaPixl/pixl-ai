import type { FastifyInstance } from 'fastify';
import type { TypedWorker } from '../worker';
import type { TypedQueue } from '../queue';
import type { BaseJobData } from '../types';
import type { ILogger } from '@saas-studio/logger';

export interface JobsPluginOptions {
  workers: TypedWorker<BaseJobData>[];
  queues?: TypedQueue<BaseJobData>[];
  logger?: ILogger;
  gracefulShutdownTimeout?: number;
}

export async function registerJobsPlugin(
  fastify: FastifyInstance,
  options: JobsPluginOptions,
): Promise<void> {
  const { workers, queues = [], logger, gracefulShutdownTimeout = 30000 } = options;

  for (const worker of workers) {
    await worker.start();
    logger?.info('Worker started', { worker: worker.name });
  }

  fastify.addHook('onClose', async () => {
    logger?.info('Shutting down job workers gracefully');

    const timeout = new Promise<void>((resolve) => {
      setTimeout(() => {
        logger?.warn('Graceful shutdown timed out, forcing close');
        resolve();
      }, gracefulShutdownTimeout);
    });

    const closeWorkers = Promise.all(
      workers.map(async (worker) => {
        try {
          await worker.close();
          logger?.info('Worker closed', { worker: worker.name });
        } catch (error) {
          logger?.error('Error closing worker', {
            worker: worker.name,
            error: error instanceof Error ? error.message : 'Unknown',
          });
        }
      }),
    );

    const closeQueues = Promise.all(
      queues.map(async (queue) => {
        try {
          await queue.close();
          logger?.info('Queue closed', { queue: queue.name });
        } catch (error) {
          logger?.error('Error closing queue', {
            queue: queue.name,
            error: error instanceof Error ? error.message : 'Unknown',
          });
        }
      }),
    );

    await Promise.race([Promise.all([closeWorkers, closeQueues]), timeout]);

    logger?.info('Job workers shutdown complete');
  });
}

declare module 'fastify' {
  interface FastifyInstance {
    jobQueues: Record<string, TypedQueue<BaseJobData>>;
  }
}

export function decorateWithQueues<TQueues extends Record<string, TypedQueue<BaseJobData>>>(
  fastify: FastifyInstance,
  queues: TQueues,
): void {
  // @ts-expect-error Fastify decorate has strict typing but we use module augmentation
  fastify.decorate('jobQueues', queues);
}
