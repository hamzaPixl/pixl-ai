import type { FastifyInstance, FastifyError, FastifyRequest, FastifyReply } from 'fastify';
import { ZodError } from 'zod';
import {
  DomainError,
  NotFoundError,
  ConflictError,
  ValidationError,
  AuthorizationError,
  AuthenticationError,
  createApiError,
  HTTP_STATUS_MAP,
  type HttpErrorCode,
} from '@saas-studio/contracts';
import type { ILogger } from '@saas-studio/logger';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFastifyInstance = FastifyInstance<any, any, any, any, any>;

export interface ErrorHandlerConfig {
  logger: ILogger;
  /** Stack traces are NEVER included in production, regardless of this setting */
  includeStack?: boolean;
  logClientErrors?: boolean;
}

function isProduction(): boolean {
  return process.env['NODE_ENV'] === 'production';
}

export function registerErrorHandler(
  fastify: AnyFastifyInstance,
  config: ErrorHandlerConfig,
): void {
  const includeStack = config.includeStack === true && !isProduction();
  const { logger, logClientErrors = false } = config;

  fastify.setErrorHandler(
    async (error: FastifyError | Error, request: FastifyRequest, reply: FastifyReply) => {
      const correlationId = (request.headers['x-correlation-id'] as string) ?? undefined;

      if (error instanceof ZodError) {
        const details = error.errors.map((e) => ({
          field: e.path.join('.'),
          message: e.message,
          code: e.code,
        }));

        const response = createApiError(
          'UNPROCESSABLE_ENTITY',
          'Validation failed',
          details,
          correlationId,
        );

        if (logClientErrors) {
          logger.warn('Validation error', {
            path: request.url,
            method: request.method,
            errors: details,
          });
        }

        return reply.status(422).send(response);
      }

      if (error instanceof DomainError) {
        const httpCode = error.httpCode as HttpErrorCode;
        const statusCode = HTTP_STATUS_MAP[httpCode] ?? 400;

        const response = createApiError(
          httpCode,
          error.message,
          error instanceof ValidationError ? error.details : undefined,
          correlationId,
        );

        if (statusCode >= 500) {
          logger.error('Domain error', {
            path: request.url,
            method: request.method,
            error: error.message,
            code: error.code,
            stack: includeStack ? error.stack : undefined,
          });
        } else if (logClientErrors) {
          logger.warn('Client error', {
            path: request.url,
            method: request.method,
            error: error.message,
            code: error.code,
          });
        }

        return reply.status(statusCode).send(response);
      }

      if ('statusCode' in error) {
        const fastifyError = error as FastifyError;
        const statusCode = fastifyError.statusCode ?? 500;
        const code = statusCode >= 500 ? 'INTERNAL_SERVER_ERROR' : 'BAD_REQUEST';

        const response = createApiError(
          code as HttpErrorCode,
          fastifyError.message,
          undefined,
          correlationId,
        );

        if (statusCode >= 500) {
          logger.error('Server error', {
            path: request.url,
            method: request.method,
            error: fastifyError.message,
            stack: includeStack ? fastifyError.stack : undefined,
          });
        }

        return reply.status(statusCode).send(response);
      }

      logger.error('Unhandled error', {
        path: request.url,
        method: request.method,
        error: error.message,
        stack: includeStack ? error.stack : undefined,
      });

      const response = createApiError(
        'INTERNAL_SERVER_ERROR',
        'An unexpected error occurred',
        undefined,
        correlationId,
      );

      return reply.status(500).send(response);
    },
  );
}

export function registerNotFoundHandler(fastify: AnyFastifyInstance): void {
  fastify.setNotFoundHandler(async (request: FastifyRequest, reply: FastifyReply) => {
    const correlationId = (request.headers['x-correlation-id'] as string) ?? undefined;

    const response = createApiError(
      'NOT_FOUND',
      `Route ${request.method} ${request.url} not found`,
      undefined,
      correlationId,
    );

    return reply.status(404).send(response);
  });
}
