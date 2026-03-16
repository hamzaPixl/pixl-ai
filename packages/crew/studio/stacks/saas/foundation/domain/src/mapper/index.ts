export interface IMapper<TEntity, TResponse> {
  toResponse(entity: TEntity): TResponse;
  toResponseArray(entities: TEntity[]): TResponse[];
  toResponseOrNull(entity: TEntity | null): TResponse | null;
}

export type InferMapperEntity<T> = T extends IMapper<infer E, unknown> ? E : never;

export type InferMapperResponse<T> = T extends IMapper<unknown, infer R> ? R : never;

export abstract class BaseMapper<TEntity, TResponse> implements IMapper<TEntity, TResponse> {
  abstract toResponse(entity: TEntity): TResponse;

  toResponseArray(entities: TEntity[]): TResponse[] {
    return entities.map((entity) => this.toResponse(entity));
  }

  toResponseOrNull(entity: TEntity | null): TResponse | null {
    return entity ? this.toResponse(entity) : null;
  }
}
