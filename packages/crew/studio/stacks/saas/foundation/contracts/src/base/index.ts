import { z } from 'zod';

import { TenantIdSchema, TimestampSchema, UuidSchema } from '../primitives';

export const BaseEntitySchema = z.object({
  id: UuidSchema,
  createdAt: TimestampSchema,
  updatedAt: TimestampSchema,
});
export type BaseEntity = z.infer<typeof BaseEntitySchema>;

export const TenantScopedSchema = BaseEntitySchema.extend({
  tenantId: TenantIdSchema,
});
export type TenantScoped = z.infer<typeof TenantScopedSchema>;

export const SoftDeletableSchema = z.object({
  deletedAt: TimestampSchema.nullable(),
});
export type SoftDeletable = z.infer<typeof SoftDeletableSchema>;

// For optimistic locking
export const VersionedSchema = z.object({
  version: z.number().int().nonnegative(),
});
export type Versioned = z.infer<typeof VersionedSchema>;

export const AuditableSchema = z.object({
  createdBy: UuidSchema.nullable(),
  updatedBy: UuidSchema.nullable(),
});
export type Auditable = z.infer<typeof AuditableSchema>;

export const FullEntitySchema = TenantScopedSchema.merge(SoftDeletableSchema)
  .merge(VersionedSchema)
  .merge(AuditableSchema);
export type FullEntity = z.infer<typeof FullEntitySchema>;

const CREATE_OMIT_KEYS = ['id', 'createdAt', 'updatedAt', 'version'] as const;
const UPDATE_OMIT_KEYS = ['id', 'createdAt', 'updatedAt'] as const;

type OmitKeys<T, K extends readonly string[]> = Omit<T, K[number]>;

export function createInputSchema<T extends z.ZodRawShape>(
  schema: z.ZodObject<T>,
): z.ZodObject<OmitKeys<T, typeof CREATE_OMIT_KEYS>> {
  const shape = schema.shape;
  const newShape = { ...shape } as Record<string, z.ZodTypeAny>;

  for (const key of CREATE_OMIT_KEYS) {
    delete newShape[key];
  }

  return z.object(newShape) as unknown as z.ZodObject<OmitKeys<T, typeof CREATE_OMIT_KEYS>>;
}

export function updateInputSchema<T extends z.ZodRawShape>(schema: z.ZodObject<T>) {
  const shape = schema.shape;
  const newShape = { ...shape } as Record<string, z.ZodTypeAny>;

  for (const key of UPDATE_OMIT_KEYS) {
    delete newShape[key];
  }

  const partial = z.object(newShape).partial();

  return z
    .object({
      id: UuidSchema,
    })
    .merge(partial);
}
