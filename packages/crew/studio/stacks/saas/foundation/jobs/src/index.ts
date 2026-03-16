export {
  BaseJobDataSchema,
  JobStatus,
  success,
  failure,
} from './types';
export type {
  BaseJobData,
  JobDefinition,
  JobOptions,
  JobStatusType,
  JobResult,
} from './types';

export { createQueue, TypedQueue } from './queue';
export type { QueueConfig } from './queue';

export { createWorker, TypedWorker } from './worker';
export type { WorkerConfig, JobHandler } from './worker';

export { createScheduler, JobScheduler, CronPatterns } from './scheduler';
export type { CronSchedule } from './scheduler';

export { registerJobsPlugin, decorateWithQueues } from './hooks';
export type { JobsPluginOptions } from './hooks';

export { Job, Queue, Worker } from 'bullmq';

import { z } from 'zod';
import type { JobDefinition, JobOptions, BaseJobData } from './types';

export function defineJob<TData extends BaseJobData>(config: {
  name: string;
  schema: z.ZodType<TData>;
  options?: JobOptions;
}): JobDefinition<TData> {
  return {
    name: config.name,
    schema: config.schema,
    options: config.options,
  };
}

// ============================================================================
// Infrastructure
// ============================================================================

export {
  JobsInfrastructure,
  createJobsInfrastructure,
  defineJobWithHandler,
} from './infrastructure';
export type {
  JobsInfrastructureOptions,
  JobRegistration,
} from './infrastructure';
