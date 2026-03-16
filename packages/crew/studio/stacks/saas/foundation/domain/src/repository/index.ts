export interface PaginationOptions {
  page?: number;
  pageSize?: number;
  cursor?: string;
}

export interface PaginatedResult<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

export interface SortOptions<T> {
  field: keyof T;
  direction: 'asc' | 'desc';
}

export interface FilterOptions {
  includeDeleted?: boolean;
}

export interface IRepository<TAggregate, TId = string> {
  findById(id: TId): Promise<TAggregate | null>;
  findByIdOrThrow(id: TId): Promise<TAggregate>;
  findAll(options?: FilterOptions): Promise<TAggregate[]>;
  findPaginated(
    pagination: PaginationOptions,
    options?: FilterOptions,
  ): Promise<PaginatedResult<TAggregate>>;
  save(aggregate: TAggregate): Promise<TAggregate>;
  delete(id: TId): Promise<void>;
  exists(id: TId): Promise<boolean>;
  count(options?: FilterOptions): Promise<number>;
}

export interface ITenantRepository<TAggregate, TId = string> extends IRepository<TAggregate, TId> {
  findByTenant(tenantId: string, options?: FilterOptions): Promise<TAggregate[]>;
  findByTenantPaginated(
    tenantId: string,
    pagination: PaginationOptions,
    options?: FilterOptions,
  ): Promise<PaginatedResult<TAggregate>>;
}

export interface IUnitOfWork {
  begin(): Promise<void>;
  commit(): Promise<void>;
  rollback(): Promise<void>;
  getRepository<T extends IRepository<unknown>>(name: string): T;
}

export interface ISpecification<T> {
  isSatisfiedBy(candidate: T): boolean;
  and(other: ISpecification<T>): ISpecification<T>;
  or(other: ISpecification<T>): ISpecification<T>;
  not(): ISpecification<T>;
}

export abstract class Specification<T> implements ISpecification<T> {
  abstract isSatisfiedBy(candidate: T): boolean;

  and(other: ISpecification<T>): ISpecification<T> {
    return new AndSpecification<T>(this, other);
  }

  or(other: ISpecification<T>): ISpecification<T> {
    return new OrSpecification<T>(this, other);
  }

  not(): ISpecification<T> {
    return new NotSpecification<T>(this);
  }
}

class AndSpecification<T> extends Specification<T> {
  constructor(
    private readonly left: ISpecification<T>,
    private readonly right: ISpecification<T>,
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return this.left.isSatisfiedBy(candidate) && this.right.isSatisfiedBy(candidate);
  }
}

class OrSpecification<T> extends Specification<T> {
  constructor(
    private readonly left: ISpecification<T>,
    private readonly right: ISpecification<T>,
  ) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return this.left.isSatisfiedBy(candidate) || this.right.isSatisfiedBy(candidate);
  }
}

class NotSpecification<T> extends Specification<T> {
  constructor(private readonly spec: ISpecification<T>) {
    super();
  }

  isSatisfiedBy(candidate: T): boolean {
    return !this.spec.isSatisfiedBy(candidate);
  }
}
