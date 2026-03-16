import { z } from 'zod';

import { CorrelationIdSchema, TenantIdSchema, TimestampSchema, UuidSchema } from '../primitives';

export const ActorTypeSchema = z.enum(['user', 'system', 'service', 'anonymous']);
export type ActorType = z.infer<typeof ActorTypeSchema>;

export const ActorSchema = z.object({
  type: ActorTypeSchema,
  id: UuidSchema.optional(),
  tenantId: TenantIdSchema,
  email: z.string().email().optional(),
  name: z.string().optional(),
});
export type Actor = z.infer<typeof ActorSchema>;

export const EventMetadataSchema = z.object({
  eventId: UuidSchema,
  eventType: z.string(),
  aggregateType: z.string(),
  aggregateId: UuidSchema,
  version: z.number().int().nonnegative(),
  occurredAt: TimestampSchema,
  correlationId: CorrelationIdSchema.optional(),
  causationId: UuidSchema.optional(),
  actor: ActorSchema,
});
export type EventMetadata = z.infer<typeof EventMetadataSchema>;

export const EventEnvelopeSchema = z.object({
  metadata: EventMetadataSchema,
  payload: z.unknown(),
});
export type EventEnvelope = z.infer<typeof EventEnvelopeSchema>;

export function typedEventEnvelopeSchema<T extends z.ZodTypeAny>(payloadSchema: T) {
  return z.object({
    metadata: EventMetadataSchema,
    payload: payloadSchema,
  });
}

export interface DomainEvent<TPayload = unknown> {
  readonly eventType: string;
  readonly aggregateType: string;
  readonly aggregateId: string;
  readonly payload: TPayload;
  readonly occurredAt: Date;
}

export const EventTypeSchema = z.enum([
  'created',
  'updated',
  'deleted',
  'archived',
  'restored',
  'published',
  'unpublished',
]);
export type EventType = z.infer<typeof EventTypeSchema>;

export function eventType(aggregate: string, action: EventType | string): string {
  return `${aggregate}.${action}`;
}
