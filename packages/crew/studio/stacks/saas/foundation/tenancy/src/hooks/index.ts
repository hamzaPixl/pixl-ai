import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { AuthorizationError } from '@saas-studio/contracts';
import type { TenantResolver } from '../resolver';

export interface TenantHookOptions {
  resolver: TenantResolver;
  required?: boolean;
  allowedTenants?: string[];
  validateTenant?: (tenantId: string) => Promise<boolean>;
}

export function createTenantHook(options: TenantHookOptions) {
  const { resolver, required = true, allowedTenants, validateTenant } = options;

  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const tenantId = resolver.resolve(request);

    if (!tenantId) {
      if (required) {
        throw new AuthorizationError('Tenant context required');
      }
      return;
    }

    if (allowedTenants && !allowedTenants.includes(tenantId)) {
      throw new AuthorizationError('Access denied for this tenant');
    }

    if (validateTenant) {
      const isValid = await validateTenant(tenantId);
      if (!isValid) {
        throw new AuthorizationError('Invalid tenant');
      }
    }

    (request as FastifyRequest & { tenantId: string }).tenantId = tenantId;
  };
}

export function registerTenantHook(fastify: FastifyInstance, options: TenantHookOptions): void {
  fastify.decorateRequest('tenantId', null);
  fastify.addHook('preHandler', createTenantHook(options));
}

export function getRequestTenantId(request: FastifyRequest): string | null {
  return (request as FastifyRequest & { tenantId?: string }).tenantId ?? null;
}

export function requireRequestTenantId(request: FastifyRequest): string {
  const tenantId = getRequestTenantId(request);
  if (!tenantId) {
    throw new AuthorizationError('Tenant context required');
  }
  return tenantId;
}

export function validateTenantAccess(
  checkAccess: (tenantId: string, request: FastifyRequest) => Promise<boolean>,
) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const tenantId = getRequestTenantId(request);
    if (!tenantId) {
      throw new AuthorizationError('Tenant context required');
    }

    const hasAccess = await checkAccess(tenantId, request);
    if (!hasAccess) {
      throw new AuthorizationError('Access denied for this tenant');
    }
  };
}
