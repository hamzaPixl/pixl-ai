import { z } from 'zod';

export const FilterOperatorSchema = z.enum([
  'eq',
  'ne',
  'gt',
  'gte',
  'lt',
  'lte',
  'in',
  'nin',
  'contains',
  'startsWith',
  'endsWith',
  'isNull',
  'isNotNull',
]);
export type FilterOperator = z.infer<typeof FilterOperatorSchema>;

export const FilterConditionSchema = z.object({
  field: z.string(),
  operator: FilterOperatorSchema,
  value: z.unknown(),
});
export type FilterCondition = z.infer<typeof FilterConditionSchema>;

// Supports format: filter[field][operator]=value
// Example: ?filter[status][eq]=active&filter[priority][in]=high,medium
export const FilterParamsSchema = z.object({
  filter: z.record(
    z.record(z.union([z.string(), z.array(z.string())]))
  ).optional(),
});
export type FilterParams = z.infer<typeof FilterParamsSchema>;

export const SearchParamsSchema = z.object({
  search: z.string().min(1).max(255).optional(),
  searchFields: z.array(z.string()).optional(),
});
export type SearchParams = z.infer<typeof SearchParamsSchema>;

export const QueryParamsSchema = FilterParamsSchema.merge(SearchParamsSchema);
export type QueryParams = z.infer<typeof QueryParamsSchema>;

export function parseFilterValue(value: string | string[], operator: FilterOperator): unknown {
  if (operator === 'in' || operator === 'nin') {
    if (Array.isArray(value)) return value;
    return value.split(',').map(v => v.trim());
  }
  if (operator === 'isNull' || operator === 'isNotNull') {
    return null;
  }
  if (value === 'true') return true;
  if (value === 'false') return false;
  const num = Number(value);
  if (!isNaN(num) && value !== '') return num;
  return value;
}

export function parseFilterParams(params: FilterParams): FilterCondition[] {
  if (!params.filter) return [];

  const conditions: FilterCondition[] = [];

  for (const [field, operators] of Object.entries(params.filter)) {
    for (const [op, value] of Object.entries(operators)) {
      const operator = FilterOperatorSchema.safeParse(op);
      if (operator.success) {
        conditions.push({
          field,
          operator: operator.data,
          value: parseFilterValue(value, operator.data),
        });
      }
    }
  }

  return conditions;
}

export interface AllowedFilter {
  field: string;
  operators: FilterOperator[];
  dbField?: string;
}

export function validateFilters(
  conditions: FilterCondition[],
  allowed: AllowedFilter[],
): { valid: FilterCondition[]; invalid: FilterCondition[] } {
  const allowedMap = new Map(allowed.map(a => [a.field, a]));
  const valid: FilterCondition[] = [];
  const invalid: FilterCondition[] = [];

  for (const condition of conditions) {
    const config = allowedMap.get(condition.field);
    if (config && config.operators.includes(condition.operator)) {
      valid.push({
        ...condition,
        field: config.dbField ?? condition.field,
      });
    } else {
      invalid.push(condition);
    }
  }

  return { valid, invalid };
}

export const DateRangeFilterSchema = z.object({
  from: z.string().datetime().optional(),
  to: z.string().datetime().optional(),
});
export type DateRangeFilter = z.infer<typeof DateRangeFilterSchema>;

export const NumberRangeFilterSchema = z.object({
  min: z.number().optional(),
  max: z.number().optional(),
});
export type NumberRangeFilter = z.infer<typeof NumberRangeFilterSchema>;
