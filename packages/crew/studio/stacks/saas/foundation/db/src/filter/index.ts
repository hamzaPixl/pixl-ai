import type { FilterCondition, FilterOperator } from "@saas-studio/contracts";

export type PrismaWhere = Record<string, unknown>;

function operatorToPrisma(operator: FilterOperator, value: unknown): unknown {
  switch (operator) {
    case "eq":
      return value;
    case "ne":
      return { not: value };
    case "gt":
      return { gt: value };
    case "gte":
      return { gte: value };
    case "lt":
      return { lt: value };
    case "lte":
      return { lte: value };
    case "in":
      return { in: value };
    case "nin":
      return { notIn: value };
    case "contains":
      return { contains: value, mode: "insensitive" };
    case "startsWith":
      return { startsWith: value, mode: "insensitive" };
    case "endsWith":
      return { endsWith: value, mode: "insensitive" };
    case "isNull":
      return null;
    case "isNotNull":
      return { not: null };
    default:
      return value;
  }
}

export function buildFilterWhere(
  conditions: FilterCondition[],
  allowedFields?: string[],
): PrismaWhere {
  const where: PrismaWhere = {};

  for (const condition of conditions) {
    if (allowedFields && !allowedFields.includes(condition.field)) {
      continue;
    }

    where[condition.field] = operatorToPrisma(condition.operator, condition.value);
  }

  return where;
}

export function buildSortOrder(
  sortBy: string | undefined,
  sortDirection: "asc" | "desc" | undefined,
  allowedFields?: string[],
  defaultField = "createdAt",
  defaultDirection: "asc" | "desc" = "desc",
): Record<string, "asc" | "desc"> {
  const field = sortBy ?? defaultField;
  const direction = sortDirection ?? defaultDirection;

  if (allowedFields && !allowedFields.includes(field)) {
    return { [defaultField]: defaultDirection };
  }

  return { [field]: direction };
}

export interface FilterBuilderConfig {
  allowedFilterFields?: string[];
  allowedSortFields?: string[];
  defaultSortField?: string;
  defaultSortDirection?: "asc" | "desc";
}

export interface FilterBuilderResult {
  where: PrismaWhere;
  orderBy: Record<string, "asc" | "desc">;
}

export function buildQueryOptions(
  conditions: FilterCondition[],
  pagination: { sortBy?: string; sortDirection?: "asc" | "desc" },
  config: FilterBuilderConfig = {},
): FilterBuilderResult {
  const {
    allowedFilterFields,
    allowedSortFields,
    defaultSortField = "createdAt",
    defaultSortDirection = "desc",
  } = config;

  return {
    where: buildFilterWhere(conditions, allowedFilterFields),
    orderBy: buildSortOrder(
      pagination.sortBy,
      pagination.sortDirection,
      allowedSortFields,
      defaultSortField,
      defaultSortDirection,
    ),
  };
}

export function mergeWhere(...clauses: PrismaWhere[]): PrismaWhere {
  const nonEmpty = clauses.filter((c) => Object.keys(c).length > 0);
  if (nonEmpty.length === 0) return {};
  if (nonEmpty.length === 1) return nonEmpty[0];
  return { AND: nonEmpty };
}

export function orWhere(...clauses: PrismaWhere[]): PrismaWhere {
  const nonEmpty = clauses.filter((c) => Object.keys(c).length > 0);
  if (nonEmpty.length === 0) return {};
  if (nonEmpty.length === 1) return nonEmpty[0];
  return { OR: nonEmpty };
}

export function buildSearchWhere(
  search: string | undefined,
  fields: string[],
): PrismaWhere {
  if (!search || !search.trim() || fields.length === 0) {
    return {};
  }

  const searchTerm = search.trim();
  const conditions = fields.map((field) => ({
    [field]: { contains: searchTerm, mode: "insensitive" },
  }));

  return orWhere(...conditions);
}
