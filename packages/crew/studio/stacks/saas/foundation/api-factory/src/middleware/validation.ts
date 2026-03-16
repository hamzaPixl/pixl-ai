import type { FastifyRequest, FastifyReply, preHandlerAsyncHookHandler } from 'fastify';
import type { z, ZodTypeAny, ZodError } from 'zod';
import { createApiError } from '@saas-studio/contracts';

const VALIDATED_BODY_KEY = Symbol('validatedBody');
const VALIDATED_QUERY_KEY = Symbol('validatedQuery');
const VALIDATED_PARAMS_KEY = Symbol('validatedParams');

declare module 'fastify' {
  interface FastifyRequest {
    [VALIDATED_BODY_KEY]?: unknown;
    [VALIDATED_QUERY_KEY]?: unknown;
    [VALIDATED_PARAMS_KEY]?: unknown;
  }
}

function formatZodErrors(error: ZodError): Array<{ field: string; message: string; code?: string }> {
  return error.errors.map((err) => ({
    field: err.path.join('.'),
    message: err.message,
    code: err.code,
  }));
}

export function validateBody<T extends ZodTypeAny>(
  schema: T,
): preHandlerAsyncHookHandler {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const result = schema.safeParse(request.body);

    if (!result.success) {
      const error = createApiError(
        'UNPROCESSABLE_ENTITY',
        'Validation failed',
        formatZodErrors(result.error),
      );
      reply.status(422).send(error);
      return;
    }

    (request as FastifyRequest & { [VALIDATED_BODY_KEY]: z.infer<T> })[VALIDATED_BODY_KEY] = result.data;
  };
}

export function validateQuery<T extends ZodTypeAny>(
  schema: T,
): preHandlerAsyncHookHandler {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const result = schema.safeParse(request.query);

    if (!result.success) {
      const error = createApiError(
        'BAD_REQUEST',
        'Invalid query parameters',
        formatZodErrors(result.error),
      );
      reply.status(400).send(error);
      return;
    }

    (request as FastifyRequest & { [VALIDATED_QUERY_KEY]: z.infer<T> })[VALIDATED_QUERY_KEY] = result.data;
  };
}

export function validateParams<T extends ZodTypeAny>(
  schema: T,
): preHandlerAsyncHookHandler {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const result = schema.safeParse(request.params);

    if (!result.success) {
      const error = createApiError(
        'BAD_REQUEST',
        'Invalid path parameters',
        formatZodErrors(result.error),
      );
      reply.status(400).send(error);
      return;
    }

    (request as FastifyRequest & { [VALIDATED_PARAMS_KEY]: z.infer<T> })[VALIDATED_PARAMS_KEY] = result.data;
  };
}

export function getValidatedBody<T>(request: FastifyRequest): T {
  const body = (request as FastifyRequest & { [VALIDATED_BODY_KEY]?: T })[VALIDATED_BODY_KEY];
  if (body === undefined) {
    throw new Error('No validated body found. Did you forget to add validateBody preHandler?');
  }
  return body;
}

export function getValidatedQuery<T>(request: FastifyRequest): T {
  const query = (request as FastifyRequest & { [VALIDATED_QUERY_KEY]?: T })[VALIDATED_QUERY_KEY];
  if (query === undefined) {
    throw new Error('No validated query found. Did you forget to add validateQuery preHandler?');
  }
  return query;
}

export function getValidatedParams<T>(request: FastifyRequest): T {
  const params = (request as FastifyRequest & { [VALIDATED_PARAMS_KEY]?: T })[VALIDATED_PARAMS_KEY];
  if (params === undefined) {
    throw new Error('No validated params found. Did you forget to add validateParams preHandler?');
  }
  return params;
}

export interface ValidationOptions {
  body?: ZodTypeAny;
  query?: ZodTypeAny;
  params?: ZodTypeAny;
}

export function createValidationHandlers(
  options: ValidationOptions,
): preHandlerAsyncHookHandler[] {
  const handlers: preHandlerAsyncHookHandler[] = [];

  if (options.params) {
    handlers.push(validateParams(options.params));
  }
  if (options.query) {
    handlers.push(validateQuery(options.query));
  }
  if (options.body) {
    handlers.push(validateBody(options.body));
  }

  return handlers;
}
