export {
  runWithContext,
  runWithContextAsync,
  getContext,
  requireContext,
  getActor,
  requireActor,
  getTenantId,
  requireTenantId,
  getUserId,
  requireUserId,
  getCorrelationId,
  hasRole,
  hasPermission,
  createSystemActor,
  createServiceActor,
  createAnonymousActor,
} from "./actor";
export type { Actor, ActorType, RequestContext } from "./actor";

export {
  JwtPayloadSchema,
  registerJwtPlugin,
  signTokenPair,
  verifyToken,
  decodeToken,
  extractPayloadFromRequest,
  payloadToActor,
  extractBearerToken,
} from "./jwt";
export type { JwtPayload, JwtConfig, TokenPair } from "./jwt";

export {
  hashPassword,
  verifyPassword,
  needsRehash,
  validatePasswordStrength,
} from "./password";
export type { PasswordHashOptions, PasswordStrengthResult } from "./password";

export {
  createAuthenticateHook,
  createContextHook,
  registerAuthHooks,
  requireAuth,
  withRequestContext,
} from "./hooks";
export type { AuthenticateOptions } from "./hooks";

export {
  generateApiKey,
  hashApiKey,
  verifyApiKey,
  apiKeyGuard,
} from "./api-key";
export type { ApiKeyConfig, ApiKeyRecord, ApiKeyLookup } from "./api-key";
