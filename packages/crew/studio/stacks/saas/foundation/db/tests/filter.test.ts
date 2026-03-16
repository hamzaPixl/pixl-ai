import { describe, it, expect } from 'vitest';
import {
  buildFilterWhere,
  buildSortOrder,
  buildQueryOptions,
  mergeWhere,
  orWhere,
  buildSearchWhere,
} from '../src/filter';
import type { FilterCondition } from '@saas-studio/contracts';

describe('Filter Builder', () => {
  describe('buildFilterWhere', () => {
    it('should build where clause for eq operator', () => {
      const conditions: FilterCondition[] = [
        { field: 'status', operator: 'eq', value: 'active' },
      ];
      const where = buildFilterWhere(conditions);
      expect(where).toEqual({ status: 'active' });
    });

    it('should build where clause for ne operator', () => {
      const conditions: FilterCondition[] = [
        { field: 'status', operator: 'ne', value: 'deleted' },
      ];
      const where = buildFilterWhere(conditions);
      expect(where).toEqual({ status: { not: 'deleted' } });
    });

    it('should build where clause for comparison operators', () => {
      const conditions: FilterCondition[] = [
        { field: 'count', operator: 'gt', value: 10 },
        { field: 'price', operator: 'lte', value: 100 },
      ];
      const where = buildFilterWhere(conditions);
      expect(where).toEqual({
        count: { gt: 10 },
        price: { lte: 100 },
      });
    });

    it('should build where clause for in/nin operators', () => {
      const conditions: FilterCondition[] = [
        { field: 'status', operator: 'in', value: ['active', 'pending'] },
        { field: 'type', operator: 'nin', value: ['archived'] },
      ];
      const where = buildFilterWhere(conditions);
      expect(where).toEqual({
        status: { in: ['active', 'pending'] },
        type: { notIn: ['archived'] },
      });
    });

    it('should build where clause for string operators', () => {
      const conditions: FilterCondition[] = [
        { field: 'title', operator: 'contains', value: 'test' },
        { field: 'name', operator: 'startsWith', value: 'A' },
        { field: 'email', operator: 'endsWith', value: '.com' },
      ];
      const where = buildFilterWhere(conditions);
      expect(where).toEqual({
        title: { contains: 'test', mode: 'insensitive' },
        name: { startsWith: 'A', mode: 'insensitive' },
        email: { endsWith: '.com', mode: 'insensitive' },
      });
    });

    it('should build where clause for null operators', () => {
      const conditions: FilterCondition[] = [
        { field: 'deletedAt', operator: 'isNull', value: null },
        { field: 'assigneeId', operator: 'isNotNull', value: null },
      ];
      const where = buildFilterWhere(conditions);
      expect(where).toEqual({
        deletedAt: null,
        assigneeId: { not: null },
      });
    });

    it('should filter by allowed fields', () => {
      const conditions: FilterCondition[] = [
        { field: 'status', operator: 'eq', value: 'active' },
        { field: 'secret', operator: 'eq', value: 'hidden' },
      ];
      const where = buildFilterWhere(conditions, ['status']);
      expect(where).toEqual({ status: 'active' });
      expect(where).not.toHaveProperty('secret');
    });
  });

  describe('buildSortOrder', () => {
    it('should build default sort order', () => {
      const order = buildSortOrder(undefined, undefined);
      expect(order).toEqual({ createdAt: 'desc' });
    });

    it('should build custom sort order', () => {
      const order = buildSortOrder('name', 'asc');
      expect(order).toEqual({ name: 'asc' });
    });

    it('should use default for disallowed fields', () => {
      const order = buildSortOrder('secret', 'asc', ['name', 'createdAt']);
      expect(order).toEqual({ createdAt: 'desc' });
    });

    it('should allow field when in allowed list', () => {
      const order = buildSortOrder('name', 'asc', ['name', 'createdAt']);
      expect(order).toEqual({ name: 'asc' });
    });

    it('should use custom defaults', () => {
      const order = buildSortOrder(undefined, undefined, [], 'updatedAt', 'asc');
      expect(order).toEqual({ updatedAt: 'asc' });
    });
  });

  describe('buildQueryOptions', () => {
    it('should combine filters and sort', () => {
      const conditions: FilterCondition[] = [
        { field: 'status', operator: 'eq', value: 'active' },
      ];
      const pagination = { sortBy: 'name', sortDirection: 'asc' as const };

      const result = buildQueryOptions(conditions, pagination);

      expect(result.where).toEqual({ status: 'active' });
      expect(result.orderBy).toEqual({ name: 'asc' });
    });

    it('should apply allowed fields configuration', () => {
      const conditions: FilterCondition[] = [
        { field: 'status', operator: 'eq', value: 'active' },
        { field: 'hidden', operator: 'eq', value: 'secret' },
      ];
      const pagination = { sortBy: 'hidden', sortDirection: 'asc' as const };

      const result = buildQueryOptions(conditions, pagination, {
        allowedFilterFields: ['status'],
        allowedSortFields: ['status', 'name'],
        defaultSortField: 'name',
      });

      expect(result.where).toEqual({ status: 'active' });
      expect(result.orderBy).toEqual({ name: 'desc' });
    });
  });

  describe('mergeWhere', () => {
    it('should return empty object for no clauses', () => {
      expect(mergeWhere()).toEqual({});
    });

    it('should return single clause unchanged', () => {
      const clause = { status: 'active' };
      expect(mergeWhere(clause)).toEqual(clause);
    });

    it('should merge multiple clauses with AND', () => {
      const clause1 = { status: 'active' };
      const clause2 = { priority: 'high' };
      expect(mergeWhere(clause1, clause2)).toEqual({
        AND: [clause1, clause2],
      });
    });

    it('should skip empty clauses', () => {
      const clause = { status: 'active' };
      expect(mergeWhere(clause, {})).toEqual(clause);
    });
  });

  describe('orWhere', () => {
    it('should return empty object for no clauses', () => {
      expect(orWhere()).toEqual({});
    });

    it('should combine clauses with OR', () => {
      const clause1 = { status: 'active' };
      const clause2 = { status: 'pending' };
      expect(orWhere(clause1, clause2)).toEqual({
        OR: [clause1, clause2],
      });
    });
  });

  describe('buildSearchWhere', () => {
    it('should return empty for no search', () => {
      expect(buildSearchWhere(undefined, ['title'])).toEqual({});
      expect(buildSearchWhere('', ['title'])).toEqual({});
      expect(buildSearchWhere('  ', ['title'])).toEqual({});
    });

    it('should return empty for no fields', () => {
      expect(buildSearchWhere('test', [])).toEqual({});
    });

    it('should build search for single field', () => {
      const where = buildSearchWhere('test', ['title']);
      expect(where).toEqual({
        title: { contains: 'test', mode: 'insensitive' },
      });
    });

    it('should build OR search for multiple fields', () => {
      const where = buildSearchWhere('test', ['title', 'description']);
      expect(where).toEqual({
        OR: [
          { title: { contains: 'test', mode: 'insensitive' } },
          { description: { contains: 'test', mode: 'insensitive' } },
        ],
      });
    });

    it('should trim search string', () => {
      const where = buildSearchWhere('  test  ', ['title']);
      expect(where).toEqual({
        title: { contains: 'test', mode: 'insensitive' },
      });
    });
  });
});
