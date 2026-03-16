import { AsyncLocalStorage } from 'node:async_hooks';
import { AuthenticationError, AuthorizationError } from '@saas-studio/contracts';

export type ActorType = 'user' | 'system' | 'service' | 'anonymous';

export interface Actor {
  type: ActorType;
  id?: string;
  tenantId: string;
  email?: string;
  name?: string;
  roles?: string[];
  permissions?: string[];
}

export interface RequestContext {
  actor: Actor;
  correlationId: string;
  requestId: string;
  startTime: number;
  metadata?: Record<string, unknown>;
}

const requestContextStorage = new AsyncLocalStorage<RequestContext>();

export function runWithContext<T>(context: RequestContext, fn: () => T): T {
  return requestContextStorage.run(context, fn);
}

export async function runWithContextAsync<T>(
  context: RequestContext,
  fn: () => Promise<T>,
): Promise<T> {
  return requestContextStorage.run(context, fn);
}

export function getContext(): RequestContext | undefined {
  return requestContextStorage.getStore();
}

export function requireContext(): RequestContext {
  const context = getContext();
  if (!context) {
    throw new Error('Request context not available. Ensure code runs within runWithContext.');
  }
  return context;
}

export function getActor(): Actor | undefined {
  return getContext()?.actor;
}

export function requireActor(): Actor {
  const actor = getActor();
  if (!actor) {
    throw new AuthenticationError('No authenticated actor in context');
  }
  return actor;
}

export function getTenantId(): string | undefined {
  return getActor()?.tenantId;
}

export function requireTenantId(): string {
  const tenantId = getTenantId();
  if (!tenantId) {
    throw new AuthorizationError('No tenant in context');
  }
  return tenantId;
}

export function getUserId(): string | undefined {
  const actor = getActor();
  return actor?.type === 'user' ? actor.id : undefined;
}

export function requireUserId(): string {
  const userId = getUserId();
  if (!userId) {
    throw new AuthenticationError('No authenticated user in context');
  }
  return userId;
}

export function getCorrelationId(): string | undefined {
  return getContext()?.correlationId;
}

export function hasRole(role: string): boolean {
  const actor = getActor();
  return actor?.roles?.includes(role) ?? false;
}

export function hasPermission(permission: string): boolean {
  const actor = getActor();
  return actor?.permissions?.includes(permission) ?? false;
}

export function createSystemActor(tenantId: string): Actor {
  return {
    type: 'system',
    tenantId,
    name: 'System',
  };
}

export function createServiceActor(tenantId: string, serviceName: string): Actor {
  return {
    type: 'service',
    tenantId,
    name: serviceName,
  };
}

export function createAnonymousActor(tenantId: string): Actor {
  return {
    type: 'anonymous',
    tenantId,
  };
}
