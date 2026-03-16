import { Worker, type Job, type WorkerOptions } from 'bullmq';
import type { Redis } from 'ioredis';
import type { ILogger } from '@saas-studio/logger';
import type { BaseJobData, JobDefinition, JobResult } from '../types';

export type JobHandler<TData extends BaseJobData, TResult = unknown> = (
  job: Job<TData>,
  logger: ILogger,
) => Promise<JobResult<TResult>>;

export interface WorkerConfig {
  connection: Redis;
  prefix?: string;
  concurrency?: number;
  limiter?: {
    max: number;
    duration: number;
  };
  logger: ILogger;
}

export function createWorker<TData extends BaseJobData, TResult = unknown>(
  definition: JobDefinition<TData>,
  handler: JobHandler<TData, TResult>,
  config: WorkerConfig,
): TypedWorker<TData, TResult> {
  const { connection, prefix = 'jobs', concurrency = 1, limiter, logger } = config;

  const workerOptions: WorkerOptions = {
    connection,
    prefix,
    concurrency,
    limiter,
    autorun: false,
  };

  const processor = async (job: Job<TData>): Promise<JobResult<TResult>> => {
    const jobLogger = logger.child({
      jobId: job.id,
      jobName: job.name,
      tenantId: job.data.tenantId,
      attempt: job.attemptsMade + 1,
    });

    jobLogger.info('Processing job');
    const startTime = Date.now();

    try {
      const validated = definition.schema.parse(job.data);
      job.data = validated;

      const result = await handler(job, jobLogger);

      const duration = Date.now() - startTime;

      if (result.success) {
        jobLogger.info('Job completed successfully', { duration });
      } else {
        jobLogger.warn('Job completed with failure', {
          duration,
          error: result.error,
          retryable: result.retryable,
        });

        if (!result.retryable) {
          throw new Error(result.error);
        }
      }

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';

      jobLogger.error('Job failed with exception', {
        duration,
        error: errorMessage,
        stack: error instanceof Error ? error.stack : undefined,
      });

      throw error;
    }
  };

  const worker = new Worker<TData, JobResult<TResult>>(definition.name, processor, workerOptions);

  return new TypedWorker(worker, definition, logger);
}

export class TypedWorker<TData extends BaseJobData, TResult = unknown> {
  constructor(
    private readonly worker: Worker<TData, JobResult<TResult>>,
    private readonly definition: JobDefinition<TData>,
    private readonly logger: ILogger,
  ) {
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.worker.on('completed', (job) => {
      this.logger.debug('Job completed event', {
        jobId: job.id,
        jobName: job.name,
      });
    });

    this.worker.on('failed', (job, error) => {
      this.logger.error('Job failed event', {
        jobId: job?.id,
        jobName: job?.name,
        error: error.message,
      });
    });

    this.worker.on('error', (error) => {
      this.logger.error('Worker error', {
        worker: this.definition.name,
        error: error.message,
      });
    });

    this.worker.on('stalled', (jobId) => {
      this.logger.warn('Job stalled', {
        worker: this.definition.name,
        jobId,
      });
    });
  }

  async start(): Promise<void> {
    await this.worker.run();
    this.logger.info('Worker started', { worker: this.definition.name });
  }

  async pause(): Promise<void> {
    await this.worker.pause();
    this.logger.info('Worker paused', { worker: this.definition.name });
  }

  async resume(): Promise<void> {
    this.worker.resume();
    this.logger.info('Worker resumed', { worker: this.definition.name });
  }

  async close(): Promise<void> {
    await this.worker.close();
    this.logger.info('Worker closed', { worker: this.definition.name });
  }

  get name(): string {
    return this.definition.name;
  }

  get raw(): Worker<TData, JobResult<TResult>> {
    return this.worker;
  }
}
