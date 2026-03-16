import type { FastifyRequest } from 'fastify';
import type { ActorContext, RouteContext } from '../controller';

export function extractActorContext(request: FastifyRequest): ActorContext {
  const actor = (request as { actor?: { tenantId: string; id?: string } }).actor;
  if (!actor) throw new Error('Unauthorized');
  return { tenantId: actor.tenantId, actorId: actor.id ?? null };
}

export function extractRouteContext(request: FastifyRequest): RouteContext {
  return {
    params: (request.params as Record<string, string>) ?? {},
    body: request.body,
    actor: extractActorContext(request),
  };
}
