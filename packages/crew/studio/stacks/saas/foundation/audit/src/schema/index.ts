import { z } from 'zod';
import { UuidSchema, TimestampSchema, TenantIdSchema } from '@saas-studio/contracts';

export const AuditEntrySchema = z.object({
  id: UuidSchema,
  tenantId: TenantIdSchema,
  aggregateType: z.string().min(1),
  aggregateId: UuidSchema,
  action: z.string().min(1),
  actorType: z.enum(['user', 'system', 'service', 'anonymous']),
  actorId: UuidSchema.nullable(),
  actorEmail: z.string().email().nullable().optional(),
  actorName: z.string().nullable().optional(),
  before: z.unknown().nullable(),
  after: z.unknown().nullable(),
  metadata: z.record(z.unknown()).nullable().optional(),
  correlationId: UuidSchema.nullable().optional(),
  requestId: UuidSchema.nullable().optional(),
  ipAddress: z.string().nullable().optional(),
  userAgent: z.string().nullable().optional(),
  occurredAt: TimestampSchema,
});

export type AuditEntry = z.infer<typeof AuditEntrySchema>;

export const CreateAuditEntrySchema = AuditEntrySchema.omit({
  id: true,
  occurredAt: true,
});

export type CreateAuditEntry = z.infer<typeof CreateAuditEntrySchema>;

export const AuditQueryParamsSchema = z.object({
  tenantId: TenantIdSchema.optional(),
  aggregateType: z.string().optional(),
  aggregateId: UuidSchema.optional(),
  actorId: UuidSchema.optional(),
  action: z.string().optional(),
  startDate: TimestampSchema.optional(),
  endDate: TimestampSchema.optional(),
  correlationId: UuidSchema.optional(),
  limit: z.number().int().positive().max(1000).default(100),
  cursor: UuidSchema.optional(),
});

export type AuditQueryParams = z.infer<typeof AuditQueryParamsSchema>;
