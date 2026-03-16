export interface ActorContext {
  tenantId: string;
  actorId: string | null;
}

export interface RouteContext {
  params: Record<string, string>;
  body: unknown;
  actor: ActorContext;
}
