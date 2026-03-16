import { z } from 'zod';
import {
  UuidSchema,
  TimestampSchema,
  TenantIdSchema,
  CorrelationIdSchema,
  EventMetadataSchema,
} from '@saas-studio/contracts';

export const OutboxStatus = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  PUBLISHED: 'PUBLISHED',
  FAILED: 'FAILED',
} as const;

export type OutboxStatusType = (typeof OutboxStatus)[keyof typeof OutboxStatus];

export const OutboxEntrySchema = z.object({
  id: UuidSchema,
  tenantId: TenantIdSchema,
  eventType: z.string().min(1),
  aggregateType: z.string().min(1),
  aggregateId: UuidSchema,
  payload: z.unknown(),
  metadata: EventMetadataSchema.optional(),
  correlationId: CorrelationIdSchema.optional(),
  causationId: UuidSchema.optional(),
  status: z.enum(['PENDING', 'PROCESSING', 'PUBLISHED', 'FAILED']),
  attempts: z.number().int().nonnegative().default(0),
  lastError: z.string().nullable().optional(),
  publishedAt: TimestampSchema.nullable().optional(),
  createdAt: TimestampSchema,
  processedAt: TimestampSchema.nullable().optional(),
});

export type OutboxEntry = z.infer<typeof OutboxEntrySchema>;

export const CreateOutboxEntrySchema = z.object({
  tenantId: TenantIdSchema,
  eventType: z.string().min(1),
  aggregateType: z.string().min(1),
  aggregateId: UuidSchema,
  payload: z.unknown(),
  correlationId: CorrelationIdSchema.optional(),
  causationId: UuidSchema.optional(),
});

export type CreateOutboxEntry = z.infer<typeof CreateOutboxEntrySchema>;
