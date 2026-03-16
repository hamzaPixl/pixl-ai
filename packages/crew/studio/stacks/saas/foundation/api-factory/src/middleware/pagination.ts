import type { FastifyRequest, FastifyReply, preHandlerAsyncHookHandler } from 'fastify';
import { z } from 'zod';
import {
  PaginationParamsSchema,
  ListParamsSchema,
  SearchParamsSchema,
  DEFAULT_PAGE_SIZE,
  MAX_PAGE_SIZE,
} from '@saas-studio/contracts';

const PAGINATION_KEY = Symbol('pagination');

export interface PaginationContext {
  page: number;
  pageSize: number;
  sortBy: string;
  sortDirection: 'asc' | 'desc';
  search?: string;
  searchFields?: string[];
}

declare module 'fastify' {
  interface FastifyRequest {
    [PAGINATION_KEY]?: PaginationContext;
  }
}

export interface PaginationMiddlewareOptions {
  defaultPageSize?: number;
  maxPageSize?: number;
  defaultSortBy?: string;
  defaultSortDirection?: 'asc' | 'desc';
  allowedSortFields?: string[];
  searchFields?: string[];
}

export function extractPagination(
  options: PaginationMiddlewareOptions = {},
): preHandlerAsyncHookHandler {
  const {
    defaultPageSize = DEFAULT_PAGE_SIZE,
    maxPageSize = MAX_PAGE_SIZE,
    defaultSortBy = 'createdAt',
    defaultSortDirection = 'desc',
    allowedSortFields = [],
    searchFields = [],
  } = options;

  const PaginationSchema = z.object({
    page: z.coerce.number().int().positive().default(1),
    pageSize: z.coerce.number().int().positive().max(maxPageSize).default(defaultPageSize),
    sortBy: z.string().default(defaultSortBy),
    sortDirection: z.enum(['asc', 'desc']).default(defaultSortDirection),
    search: z.string().min(1).max(255).optional(),
  });

  return async (request: FastifyRequest, _reply: FastifyReply) => {
    const query = request.query as Record<string, unknown>;
    const result = PaginationSchema.safeParse(query);

    let pagination: PaginationContext;

    if (result.success) {
      let sortBy = result.data.sortBy;
      if (allowedSortFields.length > 0 && !allowedSortFields.includes(sortBy)) {
        sortBy = defaultSortBy;
      }

      pagination = {
        page: result.data.page,
        pageSize: result.data.pageSize,
        sortBy,
        sortDirection: result.data.sortDirection,
        search: result.data.search,
        searchFields: searchFields.length > 0 ? searchFields : undefined,
      };
    } else {
      pagination = {
        page: 1,
        pageSize: defaultPageSize,
        sortBy: defaultSortBy,
        sortDirection: defaultSortDirection,
      };
    }

    (request as FastifyRequest & { [PAGINATION_KEY]: PaginationContext })[PAGINATION_KEY] = pagination;
  };
}

export function getPagination(request: FastifyRequest): PaginationContext {
  const pagination = (request as FastifyRequest & { [PAGINATION_KEY]?: PaginationContext })[PAGINATION_KEY];
  if (!pagination) {
    return {
      page: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      sortBy: 'createdAt',
      sortDirection: 'desc',
    };
  }
  return pagination;
}

export function calculateSkip(pagination: PaginationContext): number {
  return (pagination.page - 1) * pagination.pageSize;
}

export function toRepositoryOptions(pagination: PaginationContext): {
  page: number;
  pageSize: number;
  sortBy: string;
  sortDirection: 'asc' | 'desc';
} {
  return {
    page: pagination.page,
    pageSize: pagination.pageSize,
    sortBy: pagination.sortBy,
    sortDirection: pagination.sortDirection,
  };
}

/**
 * Query parameters for pagination extraction.
 */
export interface PaginationQuery {
  page?: string;
  pageSize?: string;
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
  search?: string;
}

export interface ExtractPaginationOptions {
  defaultPageSize?: number;
  maxPageSize?: number;
  defaultSortBy?: string;
  defaultSortDirection?: 'asc' | 'desc';
}

/**
 * Extracts pagination context directly from a query object without requiring middleware.
 * Useful for controllers that need manual pagination extraction.
 *
 * @example
 * ```typescript
 * const pagination = extractPaginationContext(request.query);
 * const result = await service.list(pagination);
 * ```
 */
export function extractPaginationContext(
  query: PaginationQuery,
  options: ExtractPaginationOptions = {},
): PaginationContext {
  const {
    defaultPageSize = DEFAULT_PAGE_SIZE,
    maxPageSize = MAX_PAGE_SIZE,
    defaultSortBy = 'createdAt',
    defaultSortDirection = 'desc',
  } = options;

  const page = query.page ? parseInt(query.page, 10) : 1;
  const requestedPageSize = query.pageSize ? parseInt(query.pageSize, 10) : defaultPageSize;
  const pageSize = Math.min(Math.max(1, requestedPageSize), maxPageSize);

  return {
    page: Number.isNaN(page) || page < 1 ? 1 : page,
    pageSize: Number.isNaN(pageSize) ? defaultPageSize : pageSize,
    sortBy: query.sortBy || defaultSortBy,
    sortDirection: query.sortDirection || defaultSortDirection,
    search: query.search,
  };
}
