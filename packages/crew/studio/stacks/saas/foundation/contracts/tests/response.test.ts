import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  ApiResponseSchema,
  ListResponseSchema,
  createApiResponse,
  createListResponse,
} from '../src/response';

describe('Response Schemas', () => {
  describe('ApiResponseSchema', () => {
    it('should validate a simple response', () => {
      const schema = ApiResponseSchema(z.object({ name: z.string() }));
      const result = schema.safeParse({ data: { name: 'test' } });
      expect(result.success).toBe(true);
    });

    it('should validate response with meta', () => {
      const schema = ApiResponseSchema(z.string());
      const result = schema.safeParse({
        data: 'hello',
        meta: { version: '1.0' },
      });
      expect(result.success).toBe(true);
    });

    it('should fail without data', () => {
      const schema = ApiResponseSchema(z.string());
      const result = schema.safeParse({ meta: {} });
      expect(result.success).toBe(false);
    });
  });

  describe('ListResponseSchema', () => {
    it('should validate paginated response', () => {
      const schema = ListResponseSchema(z.object({ id: z.string() }));
      const result = schema.safeParse({
        data: [{ id: '1' }, { id: '2' }],
        meta: {
          total: 100,
          page: 1,
          pageSize: 20,
          totalPages: 5,
          hasNextPage: true,
          hasPreviousPage: false,
        },
      });
      expect(result.success).toBe(true);
    });

    it('should fail with missing meta fields', () => {
      const schema = ListResponseSchema(z.string());
      const result = schema.safeParse({
        data: ['a', 'b'],
        meta: { total: 10 }, // missing other fields
      });
      expect(result.success).toBe(false);
    });
  });

  describe('createApiResponse', () => {
    it('should create response with data only', () => {
      const response = createApiResponse({ id: '123' });
      expect(response).toEqual({ data: { id: '123' } });
    });

    it('should create response with meta', () => {
      const response = createApiResponse('test', { source: 'api' });
      expect(response).toEqual({ data: 'test', meta: { source: 'api' } });
    });
  });

  describe('createListResponse', () => {
    it('should create list response with pagination', () => {
      const response = createListResponse(['a', 'b', 'c'], {
        page: 1,
        pageSize: 10,
        total: 25,
      });

      expect(response.data).toEqual(['a', 'b', 'c']);
      expect(response.meta).toEqual({
        total: 25,
        page: 1,
        pageSize: 10,
        totalPages: 3,
        hasNextPage: true,
        hasPreviousPage: false,
      });
    });

    it('should calculate hasNextPage correctly for last page', () => {
      const response = createListResponse(['x'], {
        page: 3,
        pageSize: 10,
        total: 25,
      });

      expect(response.meta.hasNextPage).toBe(false);
      expect(response.meta.hasPreviousPage).toBe(true);
    });

    it('should handle empty results', () => {
      const response = createListResponse([], {
        page: 1,
        pageSize: 10,
        total: 0,
      });

      expect(response.meta.totalPages).toBe(0);
      expect(response.meta.hasNextPage).toBe(false);
      expect(response.meta.hasPreviousPage).toBe(false);
    });
  });
});
