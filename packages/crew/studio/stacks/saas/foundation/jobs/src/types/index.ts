import { z } from 'zod';

export const BaseJobDataSchema = z.object({
  tenantId: z.string().uuid(),
  correlationId: z.string().uuid().optional(),
  triggeredBy: z.string().optional(),
  triggeredAt: z.string().datetime().optional(),
});

export type BaseJobData = z.infer<typeof BaseJobDataSchema>;

export interface JobDefinition<TData extends BaseJobData = BaseJobData> {
  name: string;
  schema: z.ZodType<TData>;
  options?: JobOptions;
}

export interface JobOptions {
  attempts?: number;
  backoff?: {
    type: 'exponential' | 'fixed';
    delay: number;
  };
  delay?: number;
  priority?: number;
  timeout?: number;
  removeOnComplete?: boolean | { count: number };
  removeOnFail?: boolean | { count: number };
}

export const JobStatus = {
  WAITING: 'waiting',
  ACTIVE: 'active',
  COMPLETED: 'completed',
  FAILED: 'failed',
  DELAYED: 'delayed',
  PAUSED: 'paused',
} as const;

export type JobStatusType = (typeof JobStatus)[keyof typeof JobStatus];

export interface JobResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  retryable?: boolean;
}

export function success<T>(data?: T): JobResult<T> {
  return { success: true, data };
}

export function failure(error: string, retryable = true): JobResult {
  return { success: false, error, retryable };
}
