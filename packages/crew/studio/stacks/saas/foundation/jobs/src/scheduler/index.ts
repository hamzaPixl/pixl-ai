import type { TypedQueue } from '../queue';
import type { BaseJobData, JobDefinition } from '../types';
import type { ILogger } from '@saas-studio/logger';

export interface CronSchedule<TData extends BaseJobData> {
  name: string;
  pattern: string;
  data: TData;
  timezone?: string;
  enabled?: boolean;
}

export class JobScheduler<TData extends BaseJobData> {
  private schedules = new Map<string, CronSchedule<TData>>();

  constructor(
    private readonly queue: TypedQueue<TData>,
    private readonly logger?: ILogger,
  ) {}

  register(schedule: CronSchedule<TData>): void {
    this.schedules.set(schedule.name, schedule);
    this.logger?.info('Schedule registered', {
      name: schedule.name,
      pattern: schedule.pattern,
    });
  }

  async startAll(): Promise<void> {
    for (const [name, schedule] of this.schedules) {
      if (schedule.enabled !== false) {
        await this.start(name);
      }
    }
  }

  async start(name: string): Promise<void> {
    const schedule = this.schedules.get(name);
    if (!schedule) {
      throw new Error(`Schedule '${name}' not found`);
    }

    await this.queue.addRepeatable(schedule.data, schedule.pattern, {
      jobId: `scheduled:${name}`,
    });

    this.logger?.info('Schedule started', {
      name,
      pattern: schedule.pattern,
    });
  }

  async stop(name: string): Promise<void> {
    const schedule = this.schedules.get(name);
    if (!schedule) {
      throw new Error(`Schedule '${name}' not found`);
    }

    await this.queue.removeRepeatable(schedule.pattern);

    this.logger?.info('Schedule stopped', { name });
  }

  async stopAll(): Promise<void> {
    for (const [name] of this.schedules) {
      await this.stop(name);
    }
  }

  list(): CronSchedule<TData>[] {
    return Array.from(this.schedules.values());
  }

  get(name: string): CronSchedule<TData> | undefined {
    return this.schedules.get(name);
  }
}

export const CronPatterns = {
  EVERY_MINUTE: '* * * * *',
  EVERY_5_MINUTES: '*/5 * * * *',
  EVERY_15_MINUTES: '*/15 * * * *',
  EVERY_30_MINUTES: '*/30 * * * *',
  EVERY_HOUR: '0 * * * *',
  EVERY_DAY_MIDNIGHT: '0 0 * * *',
  EVERY_DAY_NOON: '0 12 * * *',
  EVERY_WEEK_MONDAY: '0 0 * * 1',
  EVERY_MONTH_FIRST: '0 0 1 * *',
} as const;

export function createScheduler<TData extends BaseJobData>(
  queue: TypedQueue<TData>,
  logger?: ILogger,
): JobScheduler<TData> {
  return new JobScheduler(queue, logger);
}
