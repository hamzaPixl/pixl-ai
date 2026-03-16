import { AuthorizationError } from '@saas-studio/contracts';
import { getActor, hasRole as actorHasRole } from '@saas-studio/identity';
import type { Permission } from '../permissions';

export interface RoleDefinition {
  name: string;
  description: string;
  permissions: Permission[];
  inherits?: string[];
}

export class RoleRegistry {
  private roles = new Map<string, RoleDefinition>();

  register(role: RoleDefinition): void {
    this.roles.set(role.name, role);
  }

  get(name: string): RoleDefinition | undefined {
    return this.roles.get(name);
  }

  has(name: string): boolean {
    return this.roles.has(name);
  }

  all(): RoleDefinition[] {
    return Array.from(this.roles.values());
  }

  getPermissions(roleName: string, visited = new Set<string>()): Permission[] {
    // Prevent circular inheritance
    if (visited.has(roleName)) {
      return [];
    }
    visited.add(roleName);

    const role = this.roles.get(roleName);
    if (!role) {
      return [];
    }

    const permissions = new Set<Permission>(role.permissions);

    if (role.inherits) {
      for (const inheritedRole of role.inherits) {
        for (const perm of this.getPermissions(inheritedRole, visited)) {
          permissions.add(perm);
        }
      }
    }

    return Array.from(permissions);
  }

  roleHasPermission(roleName: string, permission: Permission): boolean {
    const permissions = this.getPermissions(roleName);
    return permissions.includes(permission);
  }
}

export const roleRegistry = new RoleRegistry();

export const SystemRoles = {
  SUPER_ADMIN: 'super_admin',
  ADMIN: 'admin',
  MEMBER: 'member',
  VIEWER: 'viewer',
} as const;

export function checkRole(role: string): boolean {
  return actorHasRole(role);
}

export function requireRole(role: string): void {
  if (!checkRole(role)) {
    const actor = getActor();
    throw new AuthorizationError(
      `Role required: ${role}. Actor ${actor?.id ?? 'unknown'} lacks required role.`,
    );
  }
}

export function checkAnyRole(roles: string[]): boolean {
  return roles.some(checkRole);
}

export function checkAllRoles(roles: string[]): boolean {
  return roles.every(checkRole);
}

export function requireAnyRole(roles: string[]): void {
  if (!checkAnyRole(roles)) {
    throw new AuthorizationError(`Role required: one of [${roles.join(', ')}]`);
  }
}

export function isSuperAdmin(): boolean {
  return checkRole(SystemRoles.SUPER_ADMIN);
}

export function isAdmin(): boolean {
  return checkAnyRole([SystemRoles.SUPER_ADMIN, SystemRoles.ADMIN]);
}

export function getEffectivePermissions(): Permission[] {
  const actor = getActor();
  if (!actor?.roles) {
    return [];
  }

  const permissions = new Set<Permission>();

  for (const role of actor.roles) {
    for (const perm of roleRegistry.getPermissions(role)) {
      permissions.add(perm);
    }
  }

  if (actor.permissions) {
    for (const perm of actor.permissions) {
      permissions.add(perm as Permission);
    }
  }

  return Array.from(permissions);
}
