import type { ILogger } from '@saas-studio/logger';

interface PrismaClientLike {
  $queryRawUnsafe: <T = unknown>(query: string, ...values: unknown[]) => Promise<T>;
  $executeRawUnsafe: (query: string, ...values: unknown[]) => Promise<number>;
}
import type { EventPublisher } from '../publishers';
import { OutboxStatus, type OutboxEntry } from '../schema';

export interface OutboxWorkerConfig {
  tableName?: string;
  batchSize?: number;
  pollInterval?: number;
  maxRetries?: number;
  retryDelay?: number;
  lockTimeout?: number;
}

export class OutboxWorker {
  private isRunning = false;
  private pollTimer: NodeJS.Timeout | null = null;
  private readonly config: Required<OutboxWorkerConfig>;

  constructor(
    private readonly prisma: PrismaClientLike,
    private readonly publisher: EventPublisher,
    private readonly logger: ILogger,
    config: OutboxWorkerConfig = {},
  ) {
    this.config = {
      tableName: config.tableName ?? 'outbox',
      batchSize: config.batchSize ?? 100,
      pollInterval: config.pollInterval ?? 1000,
      maxRetries: config.maxRetries ?? 5,
      retryDelay: config.retryDelay ?? 5000,
      lockTimeout: config.lockTimeout ?? 30000,
    };
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      return;
    }

    this.isRunning = true;
    await this.publisher.connect();
    this.logger.info('Outbox worker started');

    this.poll();
  }

  async stop(): Promise<void> {
    this.isRunning = false;

    if (this.pollTimer) {
      clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }

    await this.publisher.disconnect();
    this.logger.info('Outbox worker stopped');
  }

  private poll(): void {
    if (!this.isRunning) {
      return;
    }

    this.processBatch()
      .catch((error) => {
        this.logger.error('Error processing outbox batch', {
          error: error instanceof Error ? error.message : 'Unknown',
        });
      })
      .finally(() => {
        if (this.isRunning) {
          this.pollTimer = setTimeout(() => this.poll(), this.config.pollInterval);
        }
      });
  }

  private async processBatch(): Promise<void> {
    const entries = await this.fetchPendingEntries();

    if (entries.length === 0) {
      return;
    }

    this.logger.debug('Processing outbox batch', { count: entries.length });

    for (const entry of entries) {
      await this.processEntry(entry);
    }
  }

  private async fetchPendingEntries(): Promise<OutboxEntry[]> {
    const now = new Date();
    const lockUntil = new Date(now.getTime() + this.config.lockTimeout);

    const entries: OutboxEntry[] = await this.prisma.$queryRawUnsafe(
      `UPDATE ${this.config.tableName}
       SET status = $1, processed_at = $2
       WHERE id IN (
         SELECT id FROM ${this.config.tableName}
         WHERE status = $3
           AND (processed_at IS NULL OR processed_at < $4)
           AND attempts < $5
         ORDER BY created_at ASC
         LIMIT $6
         FOR UPDATE SKIP LOCKED
       )
       RETURNING *`,
      OutboxStatus.PROCESSING,
      lockUntil.toISOString(),
      OutboxStatus.PENDING,
      now.toISOString(),
      this.config.maxRetries,
      this.config.batchSize,
    );

    return entries;
  }

  private async processEntry(entry: OutboxEntry): Promise<void> {
    try {
      await this.publisher.publish(entry);

      await this.prisma.$executeRawUnsafe(
        `UPDATE ${this.config.tableName}
         SET status = $1, published_at = $2, attempts = attempts + 1
         WHERE id = $3`,
        OutboxStatus.PUBLISHED,
        new Date().toISOString(),
        entry.id,
      );

      this.logger.debug('Event published', {
        eventId: entry.id,
        eventType: entry.eventType,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const attempts = (entry.attempts ?? 0) + 1;
      const status =
        attempts >= this.config.maxRetries ? OutboxStatus.FAILED : OutboxStatus.PENDING;

      await this.prisma.$executeRawUnsafe(
        `UPDATE ${this.config.tableName}
         SET status = $1, last_error = $2, attempts = $3, processed_at = $4
         WHERE id = $5`,
        status,
        errorMessage,
        attempts,
        new Date(Date.now() + this.config.retryDelay).toISOString(),
        entry.id,
      );

      this.logger.warn('Failed to publish event', {
        eventId: entry.id,
        eventType: entry.eventType,
        attempts,
        error: errorMessage,
        willRetry: status === OutboxStatus.PENDING,
      });
    }
  }
}

export function createOutboxWorker(
  prisma: PrismaClientLike,
  publisher: EventPublisher,
  logger: ILogger,
  config?: OutboxWorkerConfig,
): OutboxWorker {
  return new OutboxWorker(prisma, publisher, logger, config);
}
