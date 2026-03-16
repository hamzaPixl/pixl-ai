import type { CreateAuditEntry } from '@saas-studio/audit';
import { createAuditWriter, type AuditWriterConfig } from '@saas-studio/audit';
import type { CreateOutboxEntry } from '../schema';
import { createOutboxWriter, type OutboxWriterConfig } from '../writer';

export interface TransactionClient {
  $executeRawUnsafe: (query: string, ...values: unknown[]) => Promise<number>;
  $queryRawUnsafe: <T = unknown>(query: string, ...values: unknown[]) => Promise<T>;
  [key: string]: unknown;
}

interface PrismaClientLike {
  $transaction: <T>(
    fn: (tx: TransactionClient) => Promise<T>,
    options?: { maxWait?: number; timeout?: number },
  ) => Promise<T>;
}

export interface UnitOfWorkResult<T> {
  result: T;
  auditEntries?: CreateAuditEntry[];
  outboxEntries?: CreateOutboxEntry[];
}

export type UnitOfWorkExecutor<T> = (tx: TransactionClient) => Promise<UnitOfWorkResult<T>>;

export interface UnitOfWorkConfig {
  auditWriter?: AuditWriterConfig;
  outboxWriter?: OutboxWriterConfig;
  maxWait?: number;
  timeout?: number;
}

export class UnitOfWork {
  private readonly auditWriter;
  private readonly outboxWriter;
  private readonly maxWait: number;
  private readonly timeout: number;

  constructor(
    private readonly prisma: PrismaClientLike,
    config: UnitOfWorkConfig = {},
  ) {
    this.auditWriter = createAuditWriter(config.auditWriter);
    this.outboxWriter = createOutboxWriter(config.outboxWriter);
    this.maxWait = config.maxWait ?? 5000;
    this.timeout = config.timeout ?? 10000;
  }

  async execute<T>(executor: UnitOfWorkExecutor<T>): Promise<T> {
    return this.prisma.$transaction(
      async (tx: TransactionClient) => {
        const { result, auditEntries = [], outboxEntries = [] } = await executor(tx);

        if (auditEntries.length > 0) {
          await this.auditWriter.writeBulk(tx, auditEntries);
        }

        if (outboxEntries.length > 0) {
          await this.outboxWriter.writeBulk(tx, outboxEntries);
        }

        return result;
      },
      {
        maxWait: this.maxWait,
        timeout: this.timeout,
      },
    );
  }

  async executeReadOnly<T>(executor: (tx: TransactionClient) => Promise<T>): Promise<T> {
    return this.prisma.$transaction(executor, {
      maxWait: this.maxWait,
      timeout: this.timeout,
    });
  }
}

export function createUnitOfWork(prisma: PrismaClientLike, config?: UnitOfWorkConfig): UnitOfWork {
  return new UnitOfWork(prisma, config);
}
