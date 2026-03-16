import type { PrismaClientLike } from "../client";
import type { ILogger } from "@saas-studio/logger";

export type TransactionIsolationLevel =
  | "ReadUncommitted"
  | "ReadCommitted"
  | "RepeatableRead"
  | "Serializable";

export type TransactionClient = Omit<
  PrismaClientLike,
  "$connect" | "$disconnect" | "$on" | "$transaction" | "$use" | "$extends"
>;

export interface TransactionOptions {
  maxWait?: number;
  timeout?: number;
  isolationLevel?: TransactionIsolationLevel;
}

export class TransactionManager {
  constructor(
    private readonly prisma: PrismaClientLike,
    private readonly logger?: ILogger,
  ) {}

  async execute<T>(
    fn: (tx: TransactionClient) => Promise<T>,
    options: TransactionOptions = {},
  ): Promise<T> {
    const startTime = Date.now();

    try {
      const result = await this.prisma.$transaction(fn, {
        maxWait: options.maxWait ?? 5000,
        timeout: options.timeout ?? 10000,
        isolationLevel: options.isolationLevel,
      });

      const duration = Date.now() - startTime;
      this.logger?.debug("Transaction completed", { duration });

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger?.error("Transaction failed", {
        duration,
        error: error instanceof Error ? error.message : "Unknown",
      });
      throw error;
    }
  }

  async executeSequence<T>(
    operations: Array<(tx: TransactionClient) => Promise<unknown>>,
    options: TransactionOptions = {},
  ): Promise<unknown[]> {
    return this.execute(async (tx) => {
      const results: unknown[] = [];
      for (const op of operations) {
        results.push(await op(tx));
      }
      return results;
    }, options);
  }

  async executeWithRetry<T>(
    fn: (tx: TransactionClient) => Promise<T>,
    options: TransactionOptions & {
      maxRetries?: number;
      retryDelay?: number;
    } = {},
  ): Promise<T> {
    const { maxRetries = 3, retryDelay = 100, ...txOptions } = options;
    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await this.execute(fn, txOptions);
      } catch (error) {
        lastError = error as Error;

        const isConflict = this.isConflictError(error);

        if (!isConflict || attempt === maxRetries) {
          throw error;
        }

        this.logger?.warn("Transaction conflict, retrying", {
          attempt,
          maxRetries,
        });

        await this.delay(retryDelay * Math.pow(2, attempt - 1));
      }
    }

    throw lastError;
  }

  private isConflictError(error: unknown): boolean {
    if (
      error !== null &&
      typeof error === "object" &&
      "code" in error &&
      typeof (error as { code: unknown }).code === "string"
    ) {
      const retryableCodes = ["P2002", "P2034"];
      return retryableCodes.includes((error as { code: string }).code);
    }
    return false;
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

export function createTransactionManager(
  prisma: PrismaClientLike,
  logger?: ILogger,
): TransactionManager {
  return new TransactionManager(prisma, logger);
}

export class BatchOperations {
  constructor(private readonly prisma: PrismaClientLike) {}

  async createMany<T>(
    model: {
      createMany: (args: {
        data: T[];
        skipDuplicates?: boolean;
      }) => Promise<{ count: number }>;
    },
    data: T[],
    options: { chunkSize?: number; skipDuplicates?: boolean } = {},
  ): Promise<number> {
    const { chunkSize = 1000, skipDuplicates = false } = options;
    let totalCreated = 0;

    for (let i = 0; i < data.length; i += chunkSize) {
      const chunk = data.slice(i, i + chunkSize);
      const result = await model.createMany({
        data: chunk,
        skipDuplicates,
      });
      totalCreated += result.count;
    }

    return totalCreated;
  }

  async updateMany<T, W>(
    model: {
      updateMany: (args: {
        where: W;
        data: Partial<T>;
      }) => Promise<{ count: number }>;
    },
    where: W,
    data: Partial<T>,
  ): Promise<number> {
    const result = await model.updateMany({ where, data });
    return result.count;
  }

  async deleteMany<W>(
    model: { deleteMany: (args: { where: W }) => Promise<{ count: number }> },
    where: W,
  ): Promise<number> {
    const result = await model.deleteMany({ where });
    return result.count;
  }
}

export function createBatchOperations(
  prisma: PrismaClientLike,
): BatchOperations {
  return new BatchOperations(prisma);
}
