import type { PrismaClientLike } from "../client";
import type { TransactionClient } from "../transaction";
import type { IPrismaSpecification } from "../specification";
import { NotFoundError, ConflictError } from "@saas-studio/contracts";
import { requireTenantId } from "@saas-studio/identity";

export interface PaginationOptions {
  page?: number;
  pageSize?: number;
  cursor?: string;
  sortBy?: string;
  sortDirection?: "asc" | "desc";
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
  direction: "asc" | "desc";
}

export interface FilterOptions {
  includeDeleted?: boolean;
}

export interface IRepository<TEntity, TId = string> {
  findById(id: TId): Promise<TEntity | null>;
  findByIdOrThrow(id: TId): Promise<TEntity>;
  findAll(options?: FilterOptions): Promise<TEntity[]>;
  findPaginated(
    pagination: PaginationOptions,
    options?: FilterOptions,
  ): Promise<PaginatedResult<TEntity>>;
  findBySpec(spec: IPrismaSpecification<TEntity>, options?: FilterOptions): Promise<TEntity[]>;
  findBySpecPaginated(
    spec: IPrismaSpecification<TEntity>,
    pagination: PaginationOptions,
    options?: FilterOptions,
  ): Promise<PaginatedResult<TEntity>>;
  countBySpec(spec: IPrismaSpecification<TEntity>, options?: FilterOptions): Promise<number>;
  save(entity: TEntity, tx?: TransactionClient): Promise<TEntity>;
  delete(id: TId, tx?: TransactionClient): Promise<void>;
  exists(id: TId): Promise<boolean>;
  count(options?: FilterOptions): Promise<number>;
}

export abstract class BaseRepository<
  TEntity,
  TId = string,
> implements IRepository<TEntity, TId> {
  constructor(protected readonly prisma: PrismaClientLike) {}

  protected abstract get model(): {
    findUnique: (args: { where: { id: TId } }) => Promise<unknown>;
    findMany: (args: unknown) => Promise<unknown[]>;
    create: (args: { data: unknown }) => Promise<unknown>;
    update: (args: { where: { id: TId }; data: unknown }) => Promise<unknown>;
    delete: (args: { where: { id: TId } }) => Promise<unknown>;
    count: (args?: unknown) => Promise<number>;
  };

  protected abstract toDomain(record: unknown): TEntity;

  protected abstract toPersistence(entity: TEntity): unknown;

  protected abstract getId(entity: TEntity): TId;

  protected abstract isNew(entity: TEntity): boolean;

  async findById(id: TId): Promise<TEntity | null> {
    const record = await this.model.findUnique({ where: { id } });
    return record ? this.toDomain(record) : null;
  }

  async findByIdOrThrow(id: TId): Promise<TEntity> {
    const entity = await this.findById(id);
    if (!entity) {
      throw new NotFoundError(
        this.constructor.name.replace("Repository", ""),
        String(id),
      );
    }
    return entity;
  }

  async findAll(options: FilterOptions = {}): Promise<TEntity[]> {
    const where = this.buildWhereClause(options);
    const records = await this.model.findMany({ where });
    return records.map((r) => this.toDomain(r));
  }

  async findPaginated(
    pagination: PaginationOptions,
    options: FilterOptions = {},
  ): Promise<PaginatedResult<TEntity>> {
    const { page = 1, pageSize = 20, sortBy = "createdAt", sortDirection = "desc" } = pagination;
    const skip = (page - 1) * pageSize;
    const where = this.buildWhereClause(options);
    const orderBy = { [sortBy]: sortDirection };

    const [records, total] = await Promise.all([
      this.model.findMany({
        where,
        skip,
        take: pageSize,
        orderBy,
      }),
      this.model.count({ where }),
    ]);

    const totalPages = Math.ceil(total / pageSize);

    return {
      data: records.map((r) => this.toDomain(r)),
      meta: {
        total,
        page,
        pageSize,
        totalPages,
        hasNext: page < totalPages,
        hasPrevious: page > 1,
      },
    };
  }

  async save(entity: TEntity, tx?: TransactionClient): Promise<TEntity> {
    const client = tx ?? this.prisma;
    const data = this.toPersistence(entity);
    const id = this.getId(entity);

    let record: unknown;

    if (this.isNew(entity)) {
      record = await (
        client as unknown as {
          [key: string]: {
            create: (args: { data: unknown }) => Promise<unknown>;
          };
        }
      )[this.getModelName()]?.create({ data });
    } else {
      record = await (
        client as unknown as {
          [key: string]: {
            update: (args: {
              where: { id: TId };
              data: unknown;
            }) => Promise<unknown>;
          };
        }
      )[this.getModelName()]?.update({ where: { id }, data });
    }

    return this.toDomain(record);
  }

  async delete(id: TId, tx?: TransactionClient): Promise<void> {
    const client = tx ?? this.prisma;
    await (
      client as unknown as {
        [key: string]: {
          delete: (args: { where: { id: TId } }) => Promise<unknown>;
        };
      }
    )[this.getModelName()]?.delete({ where: { id } });
  }

  async exists(id: TId): Promise<boolean> {
    const record = await this.model.findUnique({ where: { id } });
    return record !== null;
  }

  async count(options: FilterOptions = {}): Promise<number> {
    const where = this.buildWhereClause(options);
    return this.model.count({ where });
  }

  async findBySpec(
    spec: IPrismaSpecification<TEntity>,
    options: FilterOptions = {},
  ): Promise<TEntity[]> {
    const baseWhere = this.buildWhereClause(options);
    const specWhere = spec.toPrismaWhere();
    const where = { ...baseWhere, ...specWhere };
    const records = await this.model.findMany({ where });
    return records.map((r) => this.toDomain(r));
  }

  async findBySpecPaginated(
    spec: IPrismaSpecification<TEntity>,
    pagination: PaginationOptions,
    options: FilterOptions = {},
  ): Promise<PaginatedResult<TEntity>> {
    const { page = 1, pageSize = 20, sortBy = "createdAt", sortDirection = "desc" } = pagination;
    const skip = (page - 1) * pageSize;
    const baseWhere = this.buildWhereClause(options);
    const specWhere = spec.toPrismaWhere();
    const where = { ...baseWhere, ...specWhere };
    const orderBy = { [sortBy]: sortDirection };

    const [records, total] = await Promise.all([
      this.model.findMany({
        where,
        skip,
        take: pageSize,
        orderBy,
      }),
      this.model.count({ where }),
    ]);

    const totalPages = Math.ceil(total / pageSize);

    return {
      data: records.map((r) => this.toDomain(r)),
      meta: {
        total,
        page,
        pageSize,
        totalPages,
        hasNext: page < totalPages,
        hasPrevious: page > 1,
      },
    };
  }

  async countBySpec(
    spec: IPrismaSpecification<TEntity>,
    options: FilterOptions = {},
  ): Promise<number> {
    const baseWhere = this.buildWhereClause(options);
    const specWhere = spec.toPrismaWhere();
    const where = { ...baseWhere, ...specWhere };
    return this.model.count({ where });
  }

  protected getModelName(): string {
    return this.constructor.name.replace("Repository", "").toLowerCase();
  }

  protected buildWhereClause(options: FilterOptions): Record<string, unknown> {
    const where: Record<string, unknown> = {};

    if (!options.includeDeleted) {
      where["deletedAt"] = null;
    }

    return where;
  }
}

export abstract class TenantScopedRepository<
  TEntity,
  TId = string,
> extends BaseRepository<TEntity, TId> {
  protected override buildWhereClause(
    options: FilterOptions,
  ): Record<string, unknown> {
    const where = super.buildWhereClause(options);
    where["tenantId"] = requireTenantId();
    return where;
  }
}
