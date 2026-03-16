import type { IRepository } from '../repository';

export type { IRepository };

export interface IService {}

export interface IReadService<TEntity> extends IService {
  findAll(): Promise<TEntity[]>;
  findById(id: string): Promise<TEntity | null>;
}

export interface ICrudService<TEntity, TCreateInput, TUpdateInput> extends IReadService<TEntity> {
  create(input: TCreateInput): Promise<TEntity>;
  update(id: string, input: TUpdateInput): Promise<TEntity | null>;
  delete(id: string, actorId?: string): Promise<boolean>;
}

export abstract class BaseService<TEntity> implements IReadService<TEntity> {
  protected abstract get repository(): Pick<IRepository<TEntity>, 'findById' | 'findAll' | 'save'>;

  async findAll(): Promise<TEntity[]> {
    return this.repository.findAll();
  }

  async findById(id: string): Promise<TEntity | null> {
    return this.repository.findById(id);
  }

  protected async mutate(
    id: string,
    mutation: (entity: TEntity) => TEntity,
  ): Promise<TEntity | null> {
    const entity = await this.repository.findById(id);
    if (!entity) return null;
    const mutated = mutation(entity);
    await this.repository.save(mutated);
    return mutated;
  }
}

export type InferServiceEntity<T> = T extends IReadService<infer E> ? E : never;
export type InferCreateInput<T> = T extends ICrudService<unknown, infer C, unknown> ? C : never;
export type InferUpdateInput<T> = T extends ICrudService<unknown, unknown, infer U> ? U : never;
