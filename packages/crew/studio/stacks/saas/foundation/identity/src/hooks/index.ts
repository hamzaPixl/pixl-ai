import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { AuthenticationError } from '@saas-studio/contracts';
import { randomUUID } from 'node:crypto';
import {
  runWithContextAsync,
  type RequestContext,
  type Actor,
  createAnonymousActor,
} from '../actor';
import { extractPayloadFromRequest, payloadToActor, extractBearerToken } from '../jwt';

declare module 'fastify' {
  interface FastifyRequest {
    requestContext?: RequestContext;
  }
}

export interface AuthenticateOptions {
  optional?: boolean;
  defaultTenantId?: string;
}

export function createAuthenticateHook(options: AuthenticateOptions = {}) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const { optional = false, defaultTenantId } = options;

    const token = extractBearerToken(request.headers.authorization);

    if (!token) {
      if (!optional) {
        throw new AuthenticationError('Missing authentication token');
      }

      const tenantId = (request.headers['x-tenant-id'] as string) ?? defaultTenantId;
      if (tenantId) {
        (request as FastifyRequest & { actor: Actor }).actor = createAnonymousActor(tenantId);
      }
      return;
    }

    try {
      await request.jwtVerify();

      const payload = extractPayloadFromRequest(request);
      if (!payload) {
        throw new AuthenticationError('Invalid token payload');
      }

      const actor = payloadToActor(payload);
      (request as FastifyRequest & { actor: Actor }).actor = actor;
    } catch (error) {
      if (!optional) {
        throw new AuthenticationError(
          error instanceof Error ? error.message : 'Authentication failed',
        );
      }
    }
  };
}

export function createContextHook() {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const actor = (request as FastifyRequest & { actor?: Actor }).actor;

    if (!actor) {
      return;
    }

    const context: RequestContext = {
      actor,
      correlationId: (request.headers['x-correlation-id'] as string) ?? randomUUID(),
      requestId: (request.headers['x-request-id'] as string) ?? randomUUID(),
      startTime: Date.now(),
    };

    request.requestContext = context;

    reply.header('x-correlation-id', context.correlationId);
    reply.header('x-request-id', context.requestId);
  };
}

export function registerAuthHooks(
  fastify: FastifyInstance,
  options: AuthenticateOptions = {},
): void {
  fastify.decorateRequest('actor', null);
  fastify.decorateRequest('context', null);

  fastify.addHook('preHandler', createAuthenticateHook(options));
  fastify.addHook('preHandler', createContextHook());
}

export function requireAuth(request: FastifyRequest): asserts request is FastifyRequest & {
  actor: Actor;
  context: RequestContext;
} {
  const actor = (request as FastifyRequest & { actor?: Actor }).actor;
  if (!actor) {
    throw new AuthenticationError('Authentication required');
  }

  if (actor.type === 'anonymous') {
    throw new AuthenticationError('Anonymous access not allowed');
  }
}

export async function withRequestContext<T>(
  request: FastifyRequest,
  fn: () => Promise<T>,
): Promise<T>;
export async function withRequestContext<T>(
  request: FastifyRequest,
  fn: (context: RequestContext) => Promise<T>,
): Promise<T>;
export async function withRequestContext<T>(
  request: FastifyRequest,
  fn: ((context: RequestContext) => Promise<T>) | (() => Promise<T>),
): Promise<T> {
  const context = (request as FastifyRequest & { context?: RequestContext }).context;

  if (!context) {
    return (fn as () => Promise<T>)();
  }

  return runWithContextAsync(context, () =>
    (fn as (context: RequestContext) => Promise<T>)(context),
  );
}
