import { describe, it, expect } from 'vitest';
import {
  wrapResponse,
  wrapListResponse,
  wrapBulkResponse,
  emptyListResponse,
  fromRepositoryResult,
  deleteResponse,
  optionalResponse,
} from '../src/helpers/response';
import type { BulkResult } from '@saas-studio/contracts';

describe('Response Helpers', () => {
  describe('wrapResponse', () => {
    it('should wrap data in response format', () => {
      const result = wrapResponse({ id: '123', name: 'test' });
      expect(result).toEqual({ data: { id: '123', name: 'test' } });
    });

    it('should include meta when provided', () => {
      const result = wrapResponse('value', { source: 'api', version: 1 });
      expect(result).toEqual({
        data: 'value',
        meta: { source: 'api', version: 1 },
      });
    });
  });

  describe('wrapListResponse', () => {
    it('should create list response with pagination meta', () => {
      const result = wrapListResponse(['a', 'b', 'c'], {
        page: 1,
        pageSize: 10,
        total: 25,
      });

      expect(result.data).toEqual(['a', 'b', 'c']);
      expect(result.meta).toEqual({
        total: 25,
        page: 1,
        pageSize: 10,
        totalPages: 3,
        hasNextPage: true,
        hasPreviousPage: false,
      });
    });

    it('should calculate hasNextPage/hasPreviousPage correctly', () => {
      const result = wrapListResponse(['x'], {
        page: 2,
        pageSize: 10,
        total: 25,
      });

      expect(result.meta.hasNextPage).toBe(true);
      expect(result.meta.hasPreviousPage).toBe(true);
    });

    it('should handle last page', () => {
      const result = wrapListResponse(['x'], {
        page: 3,
        pageSize: 10,
        total: 25,
      });

      expect(result.meta.hasNextPage).toBe(false);
      expect(result.meta.hasPreviousPage).toBe(true);
    });
  });

  describe('wrapBulkResponse', () => {
    it('should wrap bulk result', () => {
      const bulkResult: BulkResult = {
        created: 5,
        failed: 1,
        errors: [{ index: 3, code: 'ERROR', message: 'Failed' }],
      };

      const result = wrapBulkResponse(bulkResult);
      expect(result).toEqual({ data: bulkResult });
    });
  });

  describe('emptyListResponse', () => {
    it('should create empty list with defaults', () => {
      const result = emptyListResponse();
      expect(result).toEqual({
        data: [],
        meta: {
          total: 0,
          page: 1,
          pageSize: 20,
          totalPages: 0,
          hasNextPage: false,
          hasPreviousPage: false,
        },
      });
    });

    it('should use provided page and pageSize', () => {
      const result = emptyListResponse(2, 50);
      expect(result.meta.page).toBe(2);
      expect(result.meta.pageSize).toBe(50);
    });
  });

  describe('fromRepositoryResult', () => {
    it('should convert repository result to API response', () => {
      const repoResult = {
        data: [{ id: '1' }, { id: '2' }],
        meta: {
          total: 10,
          page: 1,
          pageSize: 2,
          totalPages: 5,
          hasNext: true,
          hasPrevious: false,
        },
      };

      const result = fromRepositoryResult(repoResult);

      expect(result.data).toEqual([{ id: '1' }, { id: '2' }]);
      expect(result.meta.hasNextPage).toBe(true);
      expect(result.meta.hasPreviousPage).toBe(false);
    });

    it('should apply mapper function', () => {
      const repoResult = {
        data: [{ id: '1', name: 'test' }],
        meta: {
          total: 1,
          page: 1,
          pageSize: 10,
          totalPages: 1,
          hasNext: false,
          hasPrevious: false,
        },
      };

      const result = fromRepositoryResult(repoResult, (item) => ({
        id: item.id,
        displayName: item.name.toUpperCase(),
      }));

      expect(result.data[0]).toEqual({ id: '1', displayName: 'TEST' });
    });
  });

  describe('deleteResponse', () => {
    it('should return success true', () => {
      expect(deleteResponse()).toEqual({ success: true });
    });
  });

  describe('optionalResponse', () => {
    it('should wrap data when present', () => {
      const result = optionalResponse({ id: '123' });
      expect(result).toEqual({ data: { id: '123' } });
    });

    it('should return null for null input', () => {
      expect(optionalResponse(null)).toBeNull();
    });

    it('should return null for undefined input', () => {
      expect(optionalResponse(undefined)).toBeNull();
    });
  });
});
