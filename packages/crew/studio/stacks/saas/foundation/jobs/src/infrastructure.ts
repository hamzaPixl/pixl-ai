import Redis from 'ioredis';
import type { ILogger } from '@saas-studio/logger';
import type { z } from 'zod';
import { createQueue, TypedQueue } from './queue';
import { createWorker, TypedWorker, type JobHandler } from './worker';
import type { BaseJobData, JobDefinition, JobOptions } from './types';

/**
 * Options for creating a JobsInfrastructure instance.
 */
export interface JobsInfrastructureOptions {
  /** Redis connection URL or existing connection */
  redis: { url: string } | Redis;
  /** Logger instance */
  logger: ILogger;
  /** Queue prefix (default: 'jobs') */
  prefix?: string;
  /** Default job options */
  defaultJobOptions?: JobOptions;
  /** Worker concurrency (default: 5) */
  concurrency?: number;
}

/**
 * A job registration combines a job definition with its handler.
 */
export interface JobRegistration<TData extends BaseJobData = BaseJobData> {
  definition: JobDefinition<TData>;
  handler: JobHandler<TData>;
}

/**
 * Helper to define a job with its handler in one call.
 */
export function defineJobWithHandler<TData extends BaseJobData>(
  definition: JobDefinition<TData>,
  handler: JobHandler<TData>,
): JobRegistration<TData> {
  return { definition, handler };
}

/**
 * Factory function to create a JobsInfrastructure instance.
 */
export function createJobsInfrastructure(
  options: JobsInfrastructureOptions,
): JobsInfrastructure {
  return new JobsInfrastructure(options);
}

/**
 * Manages the complete lifecycle of job processing infrastructure:
 * - Redis connection
 * - Job queues
 * - Job workers
 *
 * Usage:
 * ```typescript
 * const infra = createJobsInfrastructure({
 *   redis: { url: 'redis://localhost:6379' },
 *   logger,
 *   prefix: 'myapp-jobs',
 * });
 *
 * infra.registerAll([
 *   defineJobWithHandler(SendNotificationJob, notificationHandler),
 *   defineJobWithHandler(TaskReminderJob, reminderHandler),
 * ]);
 *
 * await infra.initialize();
 * await infra.start();
 *
 * // Later:
 * await infra.enqueue('send-notification', data);
 *
 * // On shutdown:
 * await infra.shutdown();
 * ```
 */
export class JobsInfrastructure {
  private readonly options: JobsInfrastructureOptions;
  private readonly logger: ILogger;
  private readonly prefix: string;
  private readonly registrations: Map<string, JobRegistration<BaseJobData>> = new Map();
  private readonly queues: Map<string, TypedQueue<BaseJobData>> = new Map();
  private readonly workers: Map<string, TypedWorker<BaseJobData>> = new Map();
  private redis: Redis | null = null;
  private initialized = false;
  private started = false;

  constructor(options: JobsInfrastructureOptions) {
    this.options = options;
    this.logger = options.logger;
    this.prefix = options.prefix ?? 'jobs';
  }

  /**
   * Registers a single job with its handler.
   */
  register<TData extends BaseJobData>(registration: JobRegistration<TData>): this {
    if (this.initialized) {
      throw new Error('Cannot register jobs after initialization');
    }
    this.registrations.set(
      registration.definition.name,
      registration as JobRegistration<BaseJobData>,
    );
    return this;
  }

  /**
   * Registers multiple jobs with their handlers.
   * Uses type assertion to allow different job data types.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerAll(registrations: JobRegistration<any>[]): this {
    for (const reg of registrations) {
      this.register(reg);
    }
    return this;
  }

  /**
   * Initializes Redis connection, queues, and workers.
   * Must be called after registering all jobs.
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      this.logger.warn('JobsInfrastructure already initialized');
      return;
    }

    // Initialize Redis connection
    if ('url' in this.options.redis) {
      this.redis = new Redis(this.options.redis.url, {
        maxRetriesPerRequest: null,
        enableReadyCheck: false,
      });

      this.redis.on('error', (error) => {
        this.logger.error('Redis connection error', { error: error.message });
      });

      this.redis.on('connect', () => {
        this.logger.info('Redis connected for jobs');
      });
    } else {
      this.redis = this.options.redis;
    }

    // Create queues and workers for each registered job
    const queueConfig = {
      connection: this.redis,
      prefix: this.prefix,
      defaultJobOptions: this.options.defaultJobOptions,
      logger: this.logger,
    };

    const workerConfig = {
      connection: this.redis,
      prefix: this.prefix,
      concurrency: this.options.concurrency ?? 5,
      logger: this.logger,
    };

    for (const [name, registration] of this.registrations) {
      // Create queue
      const queue = createQueue(registration.definition, queueConfig);
      this.queues.set(name, queue);

      // Create worker
      const worker = createWorker(registration.definition, registration.handler, workerConfig);
      this.workers.set(name, worker);
    }

    this.initialized = true;
    this.logger.info('JobsInfrastructure initialized', {
      queues: Array.from(this.queues.keys()),
      workers: Array.from(this.workers.keys()),
    });
  }

  /**
   * Starts all workers. Call after initialize().
   */
  async start(): Promise<void> {
    if (!this.initialized) {
      throw new Error('JobsInfrastructure not initialized. Call initialize() first.');
    }
    if (this.started) {
      this.logger.warn('JobsInfrastructure already started');
      return;
    }

    for (const [, worker] of this.workers) {
      await worker.start();
    }

    this.started = true;
    this.logger.info('JobsInfrastructure workers started', {
      count: this.workers.size,
    });
  }

  /**
   * Returns a queue by name.
   */
  getQueue<TData extends BaseJobData>(name: string): TypedQueue<TData> | undefined {
    return this.queues.get(name) as TypedQueue<TData> | undefined;
  }

  /**
   * Enqueues a job by name.
   * Returns null if the queue doesn't exist.
   */
  async enqueue<TData extends BaseJobData>(name: string, data: TData): Promise<string | null> {
    const queue = this.getQueue<TData>(name);
    if (!queue) {
      this.logger.warn('Queue not found for job', { name });
      return null;
    }
    return queue.add(data);
  }

  /**
   * Returns whether the infrastructure is initialized.
   */
  get isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Returns whether workers are started.
   */
  get isStarted(): boolean {
    return this.started;
  }

  /**
   * Returns the Redis connection (if initialized).
   */
  get redisConnection(): Redis | null {
    return this.redis;
  }

  /**
   * Shuts down workers, queues, and Redis connection.
   */
  async shutdown(): Promise<void> {
    this.logger.info('JobsInfrastructure shutting down');

    // Close workers first
    for (const [, worker] of this.workers) {
      await worker.close();
    }
    this.workers.clear();

    // Close queues
    for (const [, queue] of this.queues) {
      await queue.close();
    }
    this.queues.clear();

    // Close Redis if we created it
    if (this.redis && 'url' in this.options.redis) {
      await this.redis.quit();
    }
    this.redis = null;

    this.initialized = false;
    this.started = false;
    this.logger.info('JobsInfrastructure shut down');
  }

  /**
   * Clears internal state without closing connections.
   * Used for testing.
   */
  clear(): void {
    this.queues.clear();
    this.workers.clear();
    this.registrations.clear();
    this.redis = null;
    this.initialized = false;
    this.started = false;
  }
}
