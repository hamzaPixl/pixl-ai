export { createApiFactory, createMinimalApiFactory } from './factory';
export type { ApiFactoryConfig, ApiFactory } from './factory';

export {
  registerCors,
  registerHelmet,
  registerRateLimit,
  registerSensible,
  registerSwagger,
  registerHealthChecks,
} from './plugins';
export type {
  CorsOptions,
  HelmetOptions,
  RateLimitOptions,
  SwaggerOptions,
  HealthCheckOptions,
} from './plugins';

export {
  registerCorrelationId,
  registerRequestLogging,
  registerGracefulShutdown,
  validateBody,
  validateQuery,
  validateParams,
  getValidatedBody,
  getValidatedQuery,
  getValidatedParams,
  createValidationHandlers,
  extractPagination,
  getPagination,
  calculateSkip,
  toRepositoryOptions,
  extractPaginationContext,
} from './middleware';
export type {
  ValidationOptions,
  PaginationContext,
  PaginationMiddlewareOptions,
  PaginationQuery,
  ExtractPaginationOptions,
} from './middleware';

export {
  wrapResponse,
  wrapListResponse,
  wrapBulkResponse,
  emptyListResponse,
  fromRepositoryResult,
  deleteResponse,
  optionalResponse,
} from './helpers/response';

export { registerErrorHandler, registerNotFoundHandler } from './error-handling';
export type { ErrorHandlerConfig } from './error-handling';

export {
  Controller,
  GET,
  POST,
  PATCH,
  PUT,
  DELETE,
  Hook,
  Service,
  Inject,
  Initializer,
  Destructor,
  injectablesHolder,
  getInstanceByToken,
} from 'fastify-decorators';
export { extractRouteContext, extractActorContext } from './decorators';

export type { ActorContext, RouteContext } from './controller';

export type {
  FastifyInstance,
  FastifyRequest,
  FastifyReply,
  FastifyPluginAsync,
  FastifyPluginOptions,
} from 'fastify';
