import type {
  ApiResponse,
  ListResponse,
  BulkResult,
} from '@saas-studio/contracts';

export function wrapResponse<T>(data: T, meta?: Record<string, unknown>): ApiResponse<T> {
  return {
    data,
    ...(meta && { meta }),
  };
}

export function wrapListResponse<T>(
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

export function wrapBulkResponse(result: BulkResult): { data: BulkResult } {
  return { data: result };
}

export function emptyListResponse<T>(
  page = 1,
  pageSize = 20,
): ListResponse<T> {
  return {
    data: [],
    meta: {
      total: 0,
      page,
      pageSize,
      totalPages: 0,
      hasNextPage: false,
      hasPreviousPage: false,
    },
  };
}

export function fromRepositoryResult<T, R>(
  result: {
    data: T[];
    meta: {
      total: number;
      page: number;
      pageSize: number;
      totalPages: number;
      hasNext: boolean;
      hasPrevious: boolean;
    };
  },
  mapper?: (item: T) => R,
): ListResponse<R> {
  return {
    data: mapper ? result.data.map(mapper) : (result.data as unknown as R[]),
    meta: {
      total: result.meta.total,
      page: result.meta.page,
      pageSize: result.meta.pageSize,
      totalPages: result.meta.totalPages,
      hasNextPage: result.meta.hasNext,
      hasPreviousPage: result.meta.hasPrevious,
    },
  };
}

export function deleteResponse(): { success: true } {
  return { success: true };
}

export function optionalResponse<T>(
  data: T | null | undefined,
): ApiResponse<T> | null {
  if (data === null || data === undefined) {
    return null;
  }
  return wrapResponse(data);
}
