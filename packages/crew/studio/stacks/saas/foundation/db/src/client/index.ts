import { createRequire } from "node:module";
import type { ILogger } from "@saas-studio/logger";
import {
  createTenantScopeExtension,
  type TenantScopeConfig,
} from "@saas-studio/tenancy";

export interface PrismaClientLike {
  $queryRaw: (...args: unknown[]) => Promise<unknown>;
  $disconnect: () => Promise<void>;
  $transaction: <T>(
    fn: (tx: PrismaClientLike) => Promise<T>,
    options?: {
      maxWait?: number;
      timeout?: number;
      isolationLevel?: string;
    },
  ) => Promise<T>;
  $on?: (
    event: string,
    cb: (e: { query: string; params: string; duration: number }) => void,
  ) => void;
  $extends?: (extension: unknown) => PrismaClientLike;
  [key: string]: unknown;
}

type PrismaClientConstructor = new (options?: {
  log?: Array<"query" | "info" | "warn" | "error">;
  datasourceUrl?: string;
}) => PrismaClientLike;

export interface DatabaseClientConfig {
  url?: string;
  logger?: ILogger;
  logQueries?: boolean;
  tenantScope?: TenantScopeConfig;
  poolMin?: number;
  poolMax?: number;
  clientConstructor?: PrismaClientConstructor;
}

export type ExtendedPrismaClient = PrismaClientLike;

export function createDatabaseClient(
  config: DatabaseClientConfig = {},
): ExtendedPrismaClient {
  const { logger, logQueries = false, tenantScope } = config;

  const log: Array<"query" | "info" | "warn" | "error"> = [];
  if (logQueries) {
    log.push("query");
  }
  log.push("error", "warn");

  const PrismaClientCtor =
    config.clientConstructor ?? getPrismaClientConstructor();
  let client = new PrismaClientCtor({
    log,
    datasourceUrl: config.url,
  });

  if (logger && logQueries) {
    client.$on?.(
      "query" as never,
      (e: { query: string; params: string; duration: number }) => {
        logger.debug("Database query", {
          query: e.query,
          params: e.params,
          duration: e.duration,
        });
      },
    );
  }

  if (tenantScope) {
    client = client.$extends?.(
      createTenantScopeExtension(tenantScope),
    ) as PrismaClientLike;
  }

  return client;
}

export function createStandardDatabaseClient(
  logger?: ILogger,
  options: { logQueries?: boolean; excludedModels?: string[] } = {},
): ExtendedPrismaClient {
  return createDatabaseClient({
    logger,
    logQueries: options.logQueries ?? process.env["NODE_ENV"] === "development",
    tenantScope: {
      excludedModels: options.excludedModels ?? [
        "Tenant",
        "AuditLog",
        "Outbox",
        "User",
      ],
    },
  });
}

export async function checkDatabaseConnection(
  client: PrismaClientLike,
): Promise<boolean> {
  try {
    await client.$queryRaw`SELECT 1`;
    return true;
  } catch {
    return false;
  }
}

export async function disconnectDatabase(
  client: PrismaClientLike,
): Promise<void> {
  await client.$disconnect();
}

function getPrismaClientConstructor(): PrismaClientConstructor {
  const require = createRequire(import.meta.url);
  const prismaModule = require("@prisma/client") as {
    PrismaClient?: PrismaClientConstructor;
  };
  if (!prismaModule?.PrismaClient) {
    throw new Error(
      "PrismaClient is not available. Generate a Prisma client in your service package and pass it via DatabaseClientConfig.clientConstructor.",
    );
  }
  return prismaModule.PrismaClient;
}
