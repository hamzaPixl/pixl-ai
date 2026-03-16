export {
  permission,
  crudPermissions,
  PermissionRegistry,
  permissionRegistry,
  StandardActions,
  checkPermission,
  requirePermission,
  checkAnyPermission,
  checkAllPermissions,
  requireAnyPermission,
  requireAllPermissions,
} from './permissions';
export type { Permission } from './permissions';

export {
  RoleRegistry,
  roleRegistry,
  SystemRoles,
  checkRole,
  requireRole,
  checkAnyRole,
  checkAllRoles,
  requireAnyRole,
  isSuperAdmin,
  isAdmin,
  getEffectivePermissions,
} from './roles';
export type { RoleDefinition } from './roles';

export {
  PolicyEvaluator,
  policyEvaluator,
  PolicyBuilder,
  definePolicy,
} from './policies';
export type { Policy, PolicyResult } from './policies';

export {
  permissionGuard,
  anyPermissionGuard,
  allPermissionsGuard,
  roleGuard,
  anyRoleGuard,
  policyGuard,
  RequirePermission,
  RequireRole,
  Guards,
  configureAuthorizationAuditLogger,
  getAuthorizationAuditLogger,
} from './guards';
export type { AuthorizationAuditLogger, AuthorizationAuditEntry } from './guards';
