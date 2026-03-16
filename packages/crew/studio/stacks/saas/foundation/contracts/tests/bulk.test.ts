import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  BulkCreateRequestSchema,
  BulkUpdateRequestSchema,
  BulkDeleteRequestSchema,
  BulkResultSchema,
  createBulkCreateResult,
  createBulkUpdateResult,
  createBulkDeleteResult,
  createBulkError,
} from '../src/bulk';

describe('Bulk Operation Schemas', () => {
  const ItemSchema = z.object({
    name: z.string(),
    value: z.number(),
  });

  describe('BulkCreateRequestSchema', () => {
    it('should validate array of items', () => {
      const schema = BulkCreateRequestSchema(ItemSchema);
      const result = schema.safeParse({
        items: [
          { name: 'a', value: 1 },
          { name: 'b', value: 2 },
        ],
      });
      expect(result.success).toBe(true);
    });

    it('should reject empty array', () => {
      const schema = BulkCreateRequestSchema(ItemSchema);
      const result = schema.safeParse({ items: [] });
      expect(result.success).toBe(false);
    });

    it('should reject more than 100 items', () => {
      const schema = BulkCreateRequestSchema(ItemSchema);
      const items = Array(101).fill({ name: 'test', value: 1 });
      const result = schema.safeParse({ items });
      expect(result.success).toBe(false);
    });
  });

  describe('BulkUpdateRequestSchema', () => {
    it('should validate items with id and partial updates', () => {
      const schema = BulkUpdateRequestSchema(ItemSchema);
      const result = schema.safeParse({
        items: [
          { id: '550e8400-e29b-41d4-a716-446655440000', name: 'updated' },
          { id: '550e8400-e29b-41d4-a716-446655440001', value: 42 },
        ],
      });
      expect(result.success).toBe(true);
    });

    it('should reject items without id', () => {
      const schema = BulkUpdateRequestSchema(ItemSchema);
      const result = schema.safeParse({
        items: [{ name: 'test' }], // missing id
      });
      expect(result.success).toBe(false);
    });
  });

  describe('BulkDeleteRequestSchema', () => {
    it('should validate array of UUIDs', () => {
      const result = BulkDeleteRequestSchema.safeParse({
        ids: [
          '550e8400-e29b-41d4-a716-446655440000',
          '550e8400-e29b-41d4-a716-446655440001',
        ],
      });
      expect(result.success).toBe(true);
    });

    it('should reject invalid UUIDs', () => {
      const result = BulkDeleteRequestSchema.safeParse({
        ids: ['not-a-uuid'],
      });
      expect(result.success).toBe(false);
    });

    it('should reject empty array', () => {
      const result = BulkDeleteRequestSchema.safeParse({ ids: [] });
      expect(result.success).toBe(false);
    });
  });

  describe('BulkResultSchema', () => {
    it('should validate create result', () => {
      const result = BulkResultSchema.safeParse({
        created: 5,
        failed: 0,
        errors: [],
      });
      expect(result.success).toBe(true);
    });

    it('should validate result with errors', () => {
      const result = BulkResultSchema.safeParse({
        updated: 3,
        failed: 2,
        errors: [
          { index: 1, code: 'NOT_FOUND', message: 'Item not found' },
          { index: 4, id: 'abc', code: 'CONFLICT', message: 'Duplicate' },
        ],
      });
      expect(result.success).toBe(true);
    });
  });

  describe('Helper functions', () => {
    it('createBulkCreateResult should create correct structure', () => {
      const result = createBulkCreateResult(5);
      expect(result).toEqual({
        created: 5,
        failed: 0,
        errors: [],
      });
    });

    it('createBulkUpdateResult with errors', () => {
      const errors = [createBulkError(0, 'NOT_FOUND', 'Not found', 'id-1')];
      const result = createBulkUpdateResult(4, errors);
      expect(result).toEqual({
        updated: 4,
        failed: 1,
        errors: [{ index: 0, id: 'id-1', code: 'NOT_FOUND', message: 'Not found' }],
      });
    });

    it('createBulkDeleteResult should create correct structure', () => {
      const result = createBulkDeleteResult(10);
      expect(result).toEqual({
        deleted: 10,
        failed: 0,
        errors: [],
      });
    });

    it('createBulkError should create error object', () => {
      const error = createBulkError(5, 'VALIDATION', 'Invalid data');
      expect(error).toEqual({
        index: 5,
        code: 'VALIDATION',
        message: 'Invalid data',
      });
    });

    it('createBulkError with optional id', () => {
      const error = createBulkError(5, 'NOT_FOUND', 'Not found', 'item-123');
      expect(error.id).toBe('item-123');
    });
  });
});
