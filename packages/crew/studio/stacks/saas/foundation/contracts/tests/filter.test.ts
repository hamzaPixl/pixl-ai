import { describe, it, expect } from 'vitest';
import {
  FilterOperatorSchema,
  FilterParamsSchema,
  SearchParamsSchema,
  parseFilterValue,
  parseFilterParams,
  validateFilters,
  type AllowedFilter,
} from '../src/filter';

describe('Filter Schemas', () => {
  describe('FilterOperatorSchema', () => {
    it('should accept valid operators', () => {
      const operators = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'contains', 'startsWith', 'endsWith', 'isNull', 'isNotNull'];
      for (const op of operators) {
        expect(FilterOperatorSchema.safeParse(op).success).toBe(true);
      }
    });

    it('should reject invalid operators', () => {
      expect(FilterOperatorSchema.safeParse('like').success).toBe(false);
      expect(FilterOperatorSchema.safeParse('between').success).toBe(false);
    });
  });

  describe('FilterParamsSchema', () => {
    it('should accept filter object', () => {
      const result = FilterParamsSchema.safeParse({
        filter: {
          status: { eq: 'active' },
          priority: { in: 'high,medium' },
        },
      });
      expect(result.success).toBe(true);
    });

    it('should accept empty filter', () => {
      const result = FilterParamsSchema.safeParse({});
      expect(result.success).toBe(true);
    });
  });

  describe('SearchParamsSchema', () => {
    it('should accept search string', () => {
      const result = SearchParamsSchema.safeParse({
        search: 'hello world',
        searchFields: ['title', 'description'],
      });
      expect(result.success).toBe(true);
    });

    it('should reject empty search', () => {
      const result = SearchParamsSchema.safeParse({ search: '' });
      expect(result.success).toBe(false);
    });
  });
});

describe('Filter Parsing', () => {
  describe('parseFilterValue', () => {
    it('should split comma-separated values for "in" operator', () => {
      expect(parseFilterValue('a,b,c', 'in')).toEqual(['a', 'b', 'c']);
    });

    it('should split comma-separated values for "nin" operator', () => {
      expect(parseFilterValue('x,y', 'nin')).toEqual(['x', 'y']);
    });

    it('should return null for isNull/isNotNull', () => {
      expect(parseFilterValue('anything', 'isNull')).toBeNull();
      expect(parseFilterValue('anything', 'isNotNull')).toBeNull();
    });

    it('should parse boolean strings', () => {
      expect(parseFilterValue('true', 'eq')).toBe(true);
      expect(parseFilterValue('false', 'eq')).toBe(false);
    });

    it('should parse numeric strings', () => {
      expect(parseFilterValue('42', 'eq')).toBe(42);
      expect(parseFilterValue('3.14', 'gt')).toBe(3.14);
    });

    it('should return string for non-numeric values', () => {
      expect(parseFilterValue('hello', 'eq')).toBe('hello');
    });

    it('should handle array input for "in" operator', () => {
      expect(parseFilterValue(['a', 'b'], 'in')).toEqual(['a', 'b']);
    });
  });

  describe('parseFilterParams', () => {
    it('should parse filter params to conditions', () => {
      const params = {
        filter: {
          status: { eq: 'active' },
          count: { gte: '10' },
        },
      };

      const conditions = parseFilterParams(params);
      expect(conditions).toHaveLength(2);
      expect(conditions).toContainEqual({
        field: 'status',
        operator: 'eq',
        value: 'active',
      });
      expect(conditions).toContainEqual({
        field: 'count',
        operator: 'gte',
        value: 10,
      });
    });

    it('should return empty array for no filters', () => {
      expect(parseFilterParams({})).toEqual([]);
    });

    it('should ignore invalid operators', () => {
      const params = {
        filter: {
          status: { invalid: 'value' },
          count: { eq: '5' },
        },
      };

      const conditions = parseFilterParams(params);
      expect(conditions).toHaveLength(1);
      expect(conditions[0].field).toBe('count');
    });
  });
});

describe('Filter Validation', () => {
  describe('validateFilters', () => {
    const allowedFilters: AllowedFilter[] = [
      { field: 'status', operators: ['eq', 'ne', 'in'] },
      { field: 'priority', operators: ['eq', 'in'], dbField: 'priority_level' },
      { field: 'createdAt', operators: ['gt', 'gte', 'lt', 'lte'] },
    ];

    it('should separate valid and invalid filters', () => {
      const conditions = [
        { field: 'status', operator: 'eq' as const, value: 'active' },
        { field: 'unknownField', operator: 'eq' as const, value: 'test' },
        { field: 'status', operator: 'contains' as const, value: 'act' }, // invalid operator for status
      ];

      const { valid, invalid } = validateFilters(conditions, allowedFilters);

      expect(valid).toHaveLength(1);
      expect(invalid).toHaveLength(2);
    });

    it('should map field names using dbField', () => {
      const conditions = [
        { field: 'priority', operator: 'eq' as const, value: 'high' },
      ];

      const { valid } = validateFilters(conditions, allowedFilters);

      expect(valid[0].field).toBe('priority_level');
    });

    it('should return all valid when all conditions are allowed', () => {
      const conditions = [
        { field: 'status', operator: 'in' as const, value: ['a', 'b'] },
        { field: 'createdAt', operator: 'gte' as const, value: '2024-01-01' },
      ];

      const { valid, invalid } = validateFilters(conditions, allowedFilters);

      expect(valid).toHaveLength(2);
      expect(invalid).toHaveLength(0);
    });
  });
});
