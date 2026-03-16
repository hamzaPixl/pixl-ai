import { Queue, type QueueOptions, type JobsOptions, type Job } from 'bullmq';
import type { Redis } from 'ioredis';
import type { ILogger } from '@saas-studio/logger';
import type { BaseJobData, JobDefinition, JobOptions } from '../types';

export interface QueueConfig {
  connection: Redis;
  prefix?: string;
  defaultJobOptions?: JobOptions;
  logger?: ILogger;
}

export function createQueue<TData extends BaseJobData>(
  definition: JobDefinition<TData>,
  config: QueueConfig,
): TypedQueue<TData> {
  const { connection, prefix = 'jobs', defaultJobOptions, logger } = config;

  const queueOptions: QueueOptions = {
    connection,
    prefix,
    defaultJobOptions: {
      attempts: defaultJobOptions?.attempts ?? 3,
      backoff: defaultJobOptions?.backoff ?? {
        type: 'exponential',
        delay: 1000,
      },
      removeOnComplete: defaultJobOptions?.removeOnComplete ?? { count: 100 },
      removeOnFail: defaultJobOptions?.removeOnFail ?? { count: 1000 },
    },
  };

  const queue = new Queue<TData, TData, string>(definition.name, queueOptions);

  return new TypedQueue(queue, definition, logger);
}

export class TypedQueue<TData extends BaseJobData> {
  private readonly queue: Queue<TData, TData, string>;

  constructor(
    queue: Queue<TData, TData, string>,
    private readonly definition: JobDefinition<TData>,
    private readonly logger?: ILogger,
  ) {
    this.queue = queue;
  }

  async add(data: TData, options?: JobsOptions): Promise<string> {
    const validated = this.definition.schema.parse(data);

    // @ts-expect-error BullMQ v5+ has strict named job typing, but we use simple string names
    const job = await this.queue.add(this.definition.name, validated, {
      ...this.definition.options,
      ...options,
    });

    this.logger?.info('Job added to queue', {
      queue: this.definition.name,
      jobId: job.id,
      tenantId: validated.tenantId,
    });

    return job.id ?? '';
  }

  async addBulk(jobs: Array<{ data: TData; options?: JobsOptions }>): Promise<string[]> {
    const bulkJobs = jobs.map((job) => ({
      name: this.definition.name,
      data: this.definition.schema.parse(job.data),
      opts: { ...this.definition.options, ...job.options },
    }));

    // @ts-expect-error BullMQ v5+ has strict named job typing, but we use simple string names
    const results = await this.queue.addBulk(bulkJobs);

    this.logger?.info('Bulk jobs added to queue', {
      queue: this.definition.name,
      count: results.length,
    });

    return results.map((job) => job.id ?? '');
  }

  async addDelayed(data: TData, delay: number, options?: JobsOptions): Promise<string> {
    return this.add(data, { ...options, delay });
  }

  async addRepeatable(data: TData, pattern: string, options?: JobsOptions): Promise<string> {
    const validated = this.definition.schema.parse(data);

    // @ts-expect-error BullMQ v5+ has strict named job typing, but we use simple string names
    const job = await this.queue.add(this.definition.name, validated, {
      ...this.definition.options,
      ...options,
      repeat: { pattern },
    });

    this.logger?.info('Repeatable job added to queue', {
      queue: this.definition.name,
      jobId: job.id,
      pattern,
    });

    return job.id ?? '';
  }

  async removeRepeatable(pattern: string): Promise<boolean> {
    // @ts-expect-error BullMQ v5+ has strict named job typing, but we use simple string names
    return this.queue.removeRepeatable(this.definition.name, { pattern });
  }

  get name(): string {
    return this.definition.name;
  }

  get raw(): Queue<TData> {
    return this.queue;
  }

  async pause(): Promise<void> {
    await this.queue.pause();
    this.logger?.info('Queue paused', { queue: this.definition.name });
  }

  async resume(): Promise<void> {
    await this.queue.resume();
    this.logger?.info('Queue resumed', { queue: this.definition.name });
  }

  async clean(grace: number, limit: number, status: 'completed' | 'failed'): Promise<string[]> {
    return this.queue.clean(grace, limit, status);
  }

  async close(): Promise<void> {
    await this.queue.close();
    this.logger?.info('Queue closed', { queue: this.definition.name });
  }
}
