import { z } from 'zod';

export function ApiResponseSchema<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({
    data: dataSchema,
    meta: z.record(z.unknown()).optional(),
  });
}

export type ApiResponse<T> = {
  data: T;
  meta?: Record<string, unknown>;
};

export const ListResponseMetaSchema = z.object({
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  pageSize: z.number().int().positive(),
  totalPages: z.number().int().nonnegative(),
  hasNextPage: z.boolean(),
  hasPreviousPage: z.boolean(),
});
export type ListResponseMeta = z.infer<typeof ListResponseMetaSchema>;

export function ListResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
    meta: ListResponseMetaSchema,
  });
}

export type ListResponse<T> = {
  data: T[];
  meta: ListResponseMeta;
};

export function createApiResponse<T>(data: T, meta?: Record<string, unknown>): ApiResponse<T> {
  return { data, ...(meta && { meta }) };
}

export function createListResponse<T>(
  data: T[],
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  },
): ListResponse<T> {
  const totalPages = Math.ceil(pagination.total / pagination.pageSize);
  return {
    data,
    meta: {
      total: pagination.total,
      page: pagination.page,
      pageSize: pagination.pageSize,
      totalPages,
      hasNextPage: pagination.page < totalPages,
      hasPreviousPage: pagination.page > 1,
    },
  };
}
