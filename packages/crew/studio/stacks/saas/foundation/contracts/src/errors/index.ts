import { z } from 'zod';

import { CorrelationIdSchema, TimestampSchema } from '../primitives';

export const HttpErrorCodeSchema = z.enum([
  'BAD_REQUEST',
  'UNAUTHORIZED',
  'FORBIDDEN',
  'NOT_FOUND',
  'CONFLICT',
  'UNPROCESSABLE_ENTITY',
  'TOO_MANY_REQUESTS',
  'INTERNAL_SERVER_ERROR',
  'SERVICE_UNAVAILABLE',
]);
export type HttpErrorCode = z.infer<typeof HttpErrorCodeSchema>;

export const HTTP_STATUS_MAP: Record<HttpErrorCode, number> = {
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
};

export const ValidationErrorDetailSchema = z.object({
  field: z.string(),
  message: z.string(),
  code: z.string().optional(),
});
export type ValidationErrorDetail = z.infer<typeof ValidationErrorDetailSchema>;

export const ApiErrorSchema = z.object({
  error: z.object({
    code: HttpErrorCodeSchema,
    message: z.string(),
    details: z.array(ValidationErrorDetailSchema).optional(),
    correlationId: CorrelationIdSchema.optional(),
    timestamp: TimestampSchema,
  }),
});
export type ApiError = z.infer<typeof ApiErrorSchema>;

export function createApiError(
  code: HttpErrorCode,
  message: string,
  details?: ValidationErrorDetail[],
  correlationId?: string,
): ApiError {
  return {
    error: {
      code,
      message,
      details,
      correlationId: correlationId as z.infer<typeof CorrelationIdSchema>,
      timestamp: new Date().toISOString(),
    },
  };
}

export class DomainError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly httpCode: HttpErrorCode = 'BAD_REQUEST',
  ) {
    super(message);
    this.name = 'DomainError';
  }
}

export class NotFoundError extends DomainError {
  constructor(resource: string, id: string) {
    super(`${resource} with id '${id}' not found`, 'NOT_FOUND', 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class ConflictError extends DomainError {
  constructor(message: string) {
    super(message, 'CONFLICT', 'CONFLICT');
    this.name = 'ConflictError';
  }
}

export class ValidationError extends DomainError {
  constructor(
    message: string,
    public readonly details: ValidationErrorDetail[] = [],
  ) {
    super(message, 'VALIDATION_ERROR', 'UNPROCESSABLE_ENTITY');
    this.name = 'ValidationError';
  }
}

export class AuthorizationError extends DomainError {
  constructor(message = 'You do not have permission to perform this action') {
    super(message, 'FORBIDDEN', 'FORBIDDEN');
    this.name = 'AuthorizationError';
  }
}

export class AuthenticationError extends DomainError {
  constructor(message = 'Authentication required') {
    super(message, 'UNAUTHORIZED', 'UNAUTHORIZED');
    this.name = 'AuthenticationError';
  }
}
