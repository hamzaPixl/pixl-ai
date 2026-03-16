import type { FastifyRequest, FastifyReply } from 'fastify';
import { AuthorizationError } from '@saas-studio/contracts';
import { getActor } from '@saas-studio/identity';
import {
  type Permission,
  checkPermission,
  checkAnyPermission,
  checkAllPermissions,
  requirePermission,
  requireAnyPermission,
  requireAllPermissions,
} from '../permissions';
import { checkRole, checkAnyRole, requireRole, requireAnyRole } from '../roles';
import { policyEvaluator } from '../policies';

declare module 'fastify' {
  interface FastifyRequest {
    user?: {
      sub: string;
      tenantId: string;
      permissions?: string[];
    };
  }
}

export interface AuthorizationAuditLogger {
  log(entry: AuthorizationAuditEntry): void;
}

export interface AuthorizationAuditEntry {
  timestamp: Date;
  actorId: string | null;
  actorType: 'user' | 'service' | 'system' | 'anonymous';
  tenantId: string | null;
  action: 'permission_check' | 'role_check' | 'policy_check';
  target: string | string[];
  allowed: boolean;
  resource?: {
    type: string;
    id?: string;
  };
  requestPath?: string;
  requestMethod?: string;
}

let auditLogger: AuthorizationAuditLogger | null = null;

export function configureAuthorizationAuditLogger(logger: AuthorizationAuditLogger | null): void {
  auditLogger = logger;
}

export function getAuthorizationAuditLogger(): AuthorizationAuditLogger | null {
  return auditLogger;
}

function logAuthorizationDecision(
  action: AuthorizationAuditEntry['action'],
  target: string | string[],
  allowed: boolean,
  request?: FastifyRequest,
  resource?: { type: string; id?: string },
): void {
  if (!auditLogger) return;

  const actor = getActor();

  auditLogger.log({
    timestamp: new Date(),
    actorId: actor?.id ?? null,
    actorType: actor?.type ?? 'anonymous',
    tenantId: actor?.tenantId ?? null,
    action,
    target,
    allowed,
    resource,
    requestPath: request?.url,
    requestMethod: request?.method,
  });
}

export function permissionGuard(permission: Permission) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const allowed = checkPermission(permission);
    logAuthorizationDecision('permission_check', permission, allowed, request);

    if (!allowed) {
      requirePermission(permission);
    }
  };
}

export function anyPermissionGuard(permissions: Permission[]) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const allowed = checkAnyPermission(permissions);
    logAuthorizationDecision('permission_check', permissions, allowed, request);

    if (!allowed) {
      requireAnyPermission(permissions);
    }
  };
}

export function allPermissionsGuard(permissions: Permission[]) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const allowed = checkAllPermissions(permissions);
    logAuthorizationDecision('permission_check', permissions, allowed, request);

    if (!allowed) {
      requireAllPermissions(permissions);
    }
  };
}

export function roleGuard(role: string) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const allowed = checkRole(role);
    logAuthorizationDecision('role_check', role, allowed, request);

    if (!allowed) {
      requireRole(role);
    }
  };
}

export function anyRoleGuard(roles: string[]) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const allowed = checkAnyRole(roles);
    logAuthorizationDecision('role_check', roles, allowed, request);

    if (!allowed) {
      requireAnyRole(roles);
    }
  };
}

export function policyGuard<TResource extends { id?: string }>(
  resourceType: string,
  action: string,
  getResource: (request: FastifyRequest) => TResource | Promise<TResource>,
) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const resource = await getResource(request);
    const result = await policyEvaluator.can(resourceType, action, resource);

    logAuthorizationDecision(
      'policy_check',
      `${resourceType}:${action}`,
      result.allowed,
      request,
      { type: resourceType, id: resource.id },
    );

    if (!result.allowed) {
      await policyEvaluator.authorize(resourceType, action, resource);
    }
  };
}

export function RequirePermission(permission: Permission) {
  return function (
    target: unknown,
    propertyKey: string,
    descriptor: PropertyDescriptor,
  ): PropertyDescriptor {
    const originalMethod = descriptor.value as (...args: unknown[]) => unknown;

    descriptor.value = function (...args: unknown[]) {
      requirePermission(permission);
      return originalMethod.apply(this, args);
    };

    return descriptor;
  };
}

export function RequireRole(role: string) {
  return function (
    target: unknown,
    propertyKey: string,
    descriptor: PropertyDescriptor,
  ): PropertyDescriptor {
    const originalMethod = descriptor.value as (...args: unknown[]) => unknown;

    descriptor.value = function (...args: unknown[]) {
      requireRole(role);
      return originalMethod.apply(this, args);
    };

    return descriptor;
  };
}

export const Guards = {
  authenticated: async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    if (!request.user) {
      throw new AuthorizationError('Authentication required');
    }
  },

  admin: roleGuard('admin'),

  superAdmin: roleGuard('super_admin'),

  custom: (check: (request: FastifyRequest) => boolean | Promise<boolean>, message?: string) => {
    return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
      const allowed = await check(request);
      if (!allowed) {
        throw new AuthorizationError(message ?? 'Access denied');
      }
    };
  },
};
