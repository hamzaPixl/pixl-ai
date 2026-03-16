import { requireTenantId } from '@saas-studio/identity';

interface ExtensionQueryParams {
  model: string;
  operation: string;
  args: Record<string, unknown>;
  query: (args: Record<string, unknown>) => Promise<unknown>;
}

interface PrismaExtension {
  name: string;
  query: {
    $allModels: {
      $allOperations: (params: ExtensionQueryParams) => Promise<unknown>;
    };
  };
}

export type TenantScopedModel = string;

export interface TenantScopeConfig {
  tenantIdField?: string;
  excludedModels?: string[];
}

const WRITE_OPERATIONS = ['create', 'createMany', 'upsert', 'update', 'updateMany'];
const READ_OPERATIONS = [
  'findUnique',
  'findUniqueOrThrow',
  'findFirst',
  'findFirstOrThrow',
  'findMany',
  'count',
  'aggregate',
  'groupBy',
];
const DELETE_OPERATIONS = ['delete', 'deleteMany'];

/**
 * Creates Prisma extension that automatically injects tenant_id into all queries.
 * Adds tenant_id to WHERE clauses for reads/deletes and to data for writes.
 */
export function createTenantScopeExtension(config: TenantScopeConfig = {}): PrismaExtension {
  const { tenantIdField = 'tenantId', excludedModels = ['Tenant', 'AuditLog'] } = config;

  return {
    name: 'tenant-scope',
    query: {
      $allModels: {
        async $allOperations({ model, operation, args, query }: ExtensionQueryParams) {
          if (excludedModels.includes(model)) {
            return query(args);
          }

          const tenantId = requireTenantId();

          if (READ_OPERATIONS.includes(operation)) {
            const where = (args as { where?: Record<string, unknown> }).where ?? {};
            (args as { where: Record<string, unknown> }).where = {
              ...where,
              [tenantIdField]: tenantId,
            };
          }

          if (WRITE_OPERATIONS.includes(operation)) {
            if (operation === 'createMany') {
              const data = (args as { data: Record<string, unknown>[] }).data;
              (args as { data: Record<string, unknown>[] }).data = data.map((item) => ({
                ...item,
                [tenantIdField]: tenantId,
              }));
            } else if (operation === 'create' || operation === 'upsert') {
              const data = (args as { data: Record<string, unknown> }).data;
              (args as { data: Record<string, unknown> }).data = {
                ...data,
                [tenantIdField]: tenantId,
              };
            }

            if (operation === 'update' || operation === 'updateMany' || operation === 'upsert') {
              const where = (args as { where?: Record<string, unknown> }).where ?? {};
              (args as { where: Record<string, unknown> }).where = {
                ...where,
                [tenantIdField]: tenantId,
              };
            }
          }

          if (DELETE_OPERATIONS.includes(operation)) {
            const where = (args as { where?: Record<string, unknown> }).where ?? {};
            (args as { where: Record<string, unknown> }).where = {
              ...where,
              [tenantIdField]: tenantId,
            };
          }

          return query(args);
        },
      },
    },
  };
}

export function withTenantScope<T extends Record<string, unknown>>(
  data: T,
  tenantIdField = 'tenantId',
): T & { [K in typeof tenantIdField]: string } {
  const tenantId = requireTenantId();
  return {
    ...data,
    [tenantIdField]: tenantId,
  } as T & { [K in typeof tenantIdField]: string };
}

export function tenantWhere<T extends Record<string, unknown>>(
  where: T,
  tenantIdField = 'tenantId',
): T & { [K in typeof tenantIdField]: string } {
  const tenantId = requireTenantId();
  return {
    ...where,
    [tenantIdField]: tenantId,
  } as T & { [K in typeof tenantIdField]: string };
}
