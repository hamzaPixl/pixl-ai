export type PrismaWhereClause = Record<string, unknown>;

export interface IPrismaSpecification<T> {
  isSatisfiedBy(candidate: T): boolean;
  toPrismaWhere(): PrismaWhereClause;
  and(other: IPrismaSpecification<T>): IPrismaSpecification<T>;
  or(other: IPrismaSpecification<T>): IPrismaSpecification<T>;
  not(): IPrismaSpecification<T>;
}

export abstract class PrismaSpecification<T> implements IPrismaSpecification<T> {
  abstract isSatisfiedBy(candidate: T): boolean;
  abstract toPrismaWhere(): PrismaWhereClause;

  and(other: IPrismaSpecification<T>): IPrismaSpecification<T> {
    return new AndPrismaSpecification(this, other);
  }

  or(other: IPrismaSpecification<T>): IPrismaSpecification<T> {
    return new OrPrismaSpecification(this, other);
  }

  not(): IPrismaSpecification<T> {
    return new NotPrismaSpecification(this);
  }
}

class AndPrismaSpecification<T> extends PrismaSpecification<T> {
  constructor(
    private readonly left: IPrismaSpecification<T>,
    private readonly right: IPrismaSpecification<T>,
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return this.left.isSatisfiedBy(candidate) && this.right.isSatisfiedBy(candidate);
  }

  toPrismaWhere(): PrismaWhereClause {
    return {
      AND: [this.left.toPrismaWhere(), this.right.toPrismaWhere()],
    };
  }
}

class OrPrismaSpecification<T> extends PrismaSpecification<T> {
  constructor(
    private readonly left: IPrismaSpecification<T>,
    private readonly right: IPrismaSpecification<T>,
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return this.left.isSatisfiedBy(candidate) || this.right.isSatisfiedBy(candidate);
  }

  toPrismaWhere(): PrismaWhereClause {
    return {
      OR: [this.left.toPrismaWhere(), this.right.toPrismaWhere()],
    };
  }
}

class NotPrismaSpecification<T> extends PrismaSpecification<T> {
  constructor(private readonly spec: IPrismaSpecification<T>) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return !this.spec.isSatisfiedBy(candidate);
  }

  toPrismaWhere(): PrismaWhereClause {
    return {
      NOT: this.spec.toPrismaWhere(),
    };
  }
}

export function equals<T, K extends keyof T>(
  field: K,
  value: T[K],
): PrismaSpecification<T> {
  return new FieldEqualsSpecification(field, value);
}

class FieldEqualsSpecification<T, K extends keyof T> extends PrismaSpecification<T> {
  constructor(
    private readonly field: K,
    private readonly value: T[K],
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return candidate[this.field] === this.value;
  }

  toPrismaWhere(): PrismaWhereClause {
    return { [this.field as string]: this.value };
  }
}

export function contains<T>(
  field: keyof T,
  value: string,
  mode: 'default' | 'insensitive' = 'default',
): PrismaSpecification<T> {
  return new ContainsSpecification(field, value, mode);
}

class ContainsSpecification<T> extends PrismaSpecification<T> {
  constructor(
    private readonly field: keyof T,
    private readonly value: string,
    private readonly mode: 'default' | 'insensitive',
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    const fieldValue = candidate[this.field];
    if (typeof fieldValue !== 'string') return false;
    return this.mode === 'insensitive'
      ? fieldValue.toLowerCase().includes(this.value.toLowerCase())
      : fieldValue.includes(this.value);
  }

  toPrismaWhere(): PrismaWhereClause {
    return {
      [this.field as string]: {
        contains: this.value,
        ...(this.mode === 'insensitive' ? { mode: 'insensitive' } : {}),
      },
    };
  }
}

export function isIn<T, K extends keyof T>(
  field: K,
  values: T[K][],
): PrismaSpecification<T> {
  return new InSpecification(field, values);
}

class InSpecification<T, K extends keyof T> extends PrismaSpecification<T> {
  constructor(
    private readonly field: K,
    private readonly values: T[K][],
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return this.values.includes(candidate[this.field]);
  }

  toPrismaWhere(): PrismaWhereClause {
    return { [this.field as string]: { in: this.values } };
  }
}

export function greaterThan<T, K extends keyof T>(
  field: K,
  value: T[K],
): PrismaSpecification<T> {
  return new ComparisonSpecification(field, 'gt', value);
}

export function greaterThanOrEqual<T, K extends keyof T>(
  field: K,
  value: T[K],
): PrismaSpecification<T> {
  return new ComparisonSpecification(field, 'gte', value);
}

export function lessThan<T, K extends keyof T>(
  field: K,
  value: T[K],
): PrismaSpecification<T> {
  return new ComparisonSpecification(field, 'lt', value);
}

export function lessThanOrEqual<T, K extends keyof T>(
  field: K,
  value: T[K],
): PrismaSpecification<T> {
  return new ComparisonSpecification(field, 'lte', value);
}

class ComparisonSpecification<T, K extends keyof T> extends PrismaSpecification<T> {
  constructor(
    private readonly field: K,
    private readonly operator: 'gt' | 'gte' | 'lt' | 'lte',
    private readonly value: T[K],
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    const fieldValue = candidate[this.field];
    switch (this.operator) {
      case 'gt':
        return fieldValue > this.value;
      case 'gte':
        return fieldValue >= this.value;
      case 'lt':
        return fieldValue < this.value;
      case 'lte':
        return fieldValue <= this.value;
    }
  }

  toPrismaWhere(): PrismaWhereClause {
    return { [this.field as string]: { [this.operator]: this.value } };
  }
}

export function isNull<T>(field: keyof T): PrismaSpecification<T> {
  return new NullSpecification(field, true);
}

export function isNotNull<T>(field: keyof T): PrismaSpecification<T> {
  return new NullSpecification(field, false);
}

class NullSpecification<T> extends PrismaSpecification<T> {
  constructor(
    private readonly field: keyof T,
    private readonly isNullCheck: boolean,
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    const isFieldNull = candidate[this.field] === null || candidate[this.field] === undefined;
    return this.isNullCheck ? isFieldNull : !isFieldNull;
  }

  toPrismaWhere(): PrismaWhereClause {
    return {
      [this.field as string]: this.isNullCheck ? null : { not: null },
    };
  }
}

export function between<T, K extends keyof T>(
  field: K,
  from: T[K],
  to: T[K],
): PrismaSpecification<T> {
  return new BetweenSpecification(field, from, to);
}

class BetweenSpecification<T, K extends keyof T> extends PrismaSpecification<T> {
  constructor(
    private readonly field: K,
    private readonly from: T[K],
    private readonly to: T[K],
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    const value = candidate[this.field];
    return value >= this.from && value <= this.to;
  }

  toPrismaWhere(): PrismaWhereClause {
    return {
      [this.field as string]: {
        gte: this.from,
        lte: this.to,
      },
    };
  }
}

export function alwaysTrue<T>(): PrismaSpecification<T> {
  return new TrueSpecification();
}

class TrueSpecification<T> extends PrismaSpecification<T> {
  isSatisfiedBy(_candidate: T): boolean {
    return true;
  }

  toPrismaWhere(): PrismaWhereClause {
    return {};
  }
}

export function alwaysFalse<T>(): PrismaSpecification<T> {
  return new FalseSpecification();
}

class FalseSpecification<T> extends PrismaSpecification<T> {
  isSatisfiedBy(_candidate: T): boolean {
    return false;
  }

  toPrismaWhere(): PrismaWhereClause {
    // Using an impossible condition
    return { AND: [{ id: null }, { id: { not: null } }] };
  }
}
