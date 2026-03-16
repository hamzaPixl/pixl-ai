export {
  HeaderTenantResolver,
  SubdomainTenantResolver,
  PathTenantResolver,
  JwtTenantResolver,
  CompositeTenantResolver,
  createDefaultResolver,
} from './resolver';
export type { TenantResolver, TenantResolutionStrategy } from './resolver';

export {
  createTenantScopeExtension,
  withTenantScope,
  tenantWhere,
} from './scope';
export type { TenantScopeConfig, TenantScopedModel } from './scope';

export {
  createTenantHook,
  registerTenantHook,
  getRequestTenantId,
  requireRequestTenantId,
  validateTenantAccess,
} from './hooks';
export type { TenantHookOptions } from './hooks';
