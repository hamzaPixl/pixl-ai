import { z } from 'zod';

import { NonNegativeIntSchema, PositiveIntSchema } from '../primitives';

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

export const PaginationParamsSchema = z.object({
  page: PositiveIntSchema.default(1),
  pageSize: PositiveIntSchema.max(MAX_PAGE_SIZE).default(DEFAULT_PAGE_SIZE),
});
export type PaginationParams = z.infer<typeof PaginationParamsSchema>;

export const CursorPaginationParamsSchema = z.object({
  cursor: z.string().optional(),
  limit: PositiveIntSchema.max(MAX_PAGE_SIZE).default(DEFAULT_PAGE_SIZE),
});
export type CursorPaginationParams = z.infer<typeof CursorPaginationParamsSchema>;

export const SortDirectionSchema = z.enum(['asc', 'desc']);
export type SortDirection = z.infer<typeof SortDirectionSchema>;

export const SortParamsSchema = z.object({
  sortBy: z.string().default('createdAt'),
  sortDirection: SortDirectionSchema.default('desc'),
});
export type SortParams = z.infer<typeof SortParamsSchema>;

export const ListParamsSchema = PaginationParamsSchema.merge(SortParamsSchema);
export type ListParams = z.infer<typeof ListParamsSchema>;

export const PaginationMetaSchema = z.object({
  page: PositiveIntSchema,
  pageSize: PositiveIntSchema,
  totalItems: NonNegativeIntSchema,
  totalPages: NonNegativeIntSchema,
  hasNextPage: z.boolean(),
  hasPreviousPage: z.boolean(),
});
export type PaginationMeta = z.infer<typeof PaginationMetaSchema>;

export const CursorPaginationMetaSchema = z.object({
  nextCursor: z.string().nullable(),
  previousCursor: z.string().nullable(),
  hasMore: z.boolean(),
});
export type CursorPaginationMeta = z.infer<typeof CursorPaginationMetaSchema>;

export function paginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
    meta: PaginationMetaSchema,
  });
}

export function cursorPaginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
    meta: CursorPaginationMetaSchema,
  });
}

export function calculatePaginationMeta(
  page: number,
  pageSize: number,
  totalItems: number,
): PaginationMeta {
  const totalPages = Math.ceil(totalItems / pageSize);
  return {
    page,
    pageSize,
    totalItems,
    totalPages,
    hasNextPage: page < totalPages,
    hasPreviousPage: page > 1,
  };
}

export function calculateOffset(page: number, pageSize: number): number {
  return (page - 1) * pageSize;
}
