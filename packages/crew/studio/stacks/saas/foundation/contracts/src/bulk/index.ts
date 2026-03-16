import { z } from 'zod';

import { UuidSchema } from '../primitives';

export function BulkCreateRequestSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema).min(1).max(100),
  });
}

export type BulkCreateRequest<T> = {
  items: T[];
};

export function BulkUpdateItemSchema<T extends z.ZodRawShape>(itemSchema: z.ZodObject<T>) {
  return z.object({
    id: UuidSchema,
  }).merge(itemSchema.partial());
}

export function BulkUpdateRequestSchema<T extends z.ZodRawShape>(itemSchema: z.ZodObject<T>) {
  return z.object({
    items: z.array(BulkUpdateItemSchema(itemSchema)).min(1).max(100),
  });
}

export type BulkUpdateRequest<T> = {
  items: Array<{ id: string } & Partial<T>>;
};

export const BulkDeleteRequestSchema = z.object({
  ids: z.array(UuidSchema).min(1).max(100),
});
export type BulkDeleteRequest = z.infer<typeof BulkDeleteRequestSchema>;

export const BulkOperationErrorSchema = z.object({
  index: z.number().int().nonnegative(),
  id: z.string().optional(),
  code: z.string(),
  message: z.string(),
});
export type BulkOperationError = z.infer<typeof BulkOperationErrorSchema>;

export const BulkResultSchema = z.object({
  created: z.number().int().nonnegative().optional(),
  updated: z.number().int().nonnegative().optional(),
  deleted: z.number().int().nonnegative().optional(),
  failed: z.number().int().nonnegative(),
  errors: z.array(BulkOperationErrorSchema),
});
export type BulkResult = z.infer<typeof BulkResultSchema>;

export function createBulkCreateResult(
  created: number,
  errors: BulkOperationError[] = [],
): BulkResult {
  return {
    created,
    failed: errors.length,
    errors,
  };
}

export function createBulkUpdateResult(
  updated: number,
  errors: BulkOperationError[] = [],
): BulkResult {
  return {
    updated,
    failed: errors.length,
    errors,
  };
}

export function createBulkDeleteResult(
  deleted: number,
  errors: BulkOperationError[] = [],
): BulkResult {
  return {
    deleted,
    failed: errors.length,
    errors,
  };
}

export function createBulkError(
  index: number,
  code: string,
  message: string,
  id?: string,
): BulkOperationError {
  return { index, code, message, ...(id && { id }) };
}
