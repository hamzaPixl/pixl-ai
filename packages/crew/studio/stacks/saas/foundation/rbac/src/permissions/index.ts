import { AuthorizationError } from '@saas-studio/contracts';
import { getActor, hasPermission as actorHasPermission } from '@saas-studio/identity';

// Permission format: resource:action (e.g., invoices:create, users:read)
export type Permission = `${string}:${string}`;

export const StandardActions = {
  CREATE: 'create',
  READ: 'read',
  UPDATE: 'update',
  DELETE: 'delete',
  LIST: 'list',
} as const;

export function permission(resource: string, action: string): Permission {
  return `${resource}:${action}`;
}

export function crudPermissions(resource: string): Permission[] {
  return [
    permission(resource, StandardActions.CREATE),
    permission(resource, StandardActions.READ),
    permission(resource, StandardActions.UPDATE),
    permission(resource, StandardActions.DELETE),
    permission(resource, StandardActions.LIST),
  ];
}

export class PermissionRegistry {
  private permissions = new Map<
    string,
    { description: string; resource: string; action: string }
  >();

  register(perm: Permission, description: string): void {
    const [resource, action] = perm.split(':') as [string, string];
    this.permissions.set(perm, { description, resource, action });
  }

  registerCrud(resource: string, descriptions?: Record<string, string>): void {
    const defaultDescriptions: Record<string, string> = {
      create: `Create ${resource}`,
      read: `Read ${resource}`,
      update: `Update ${resource}`,
      delete: `Delete ${resource}`,
      list: `List ${resource}`,
    };

    const descs = { ...defaultDescriptions, ...descriptions };

    for (const action of Object.values(StandardActions)) {
      this.register(permission(resource, action), descs[action] ?? `${action} ${resource}`);
    }
  }

  has(perm: Permission): boolean {
    return this.permissions.has(perm);
  }

  get(perm: Permission): { description: string; resource: string; action: string } | undefined {
    return this.permissions.get(perm);
  }

  all(): Permission[] {
    return Array.from(this.permissions.keys()) as Permission[];
  }

  byResource(): Map<string, Permission[]> {
    const result = new Map<string, Permission[]>();

    for (const perm of this.permissions.keys()) {
      const [resource] = perm.split(':') as [string, string];
      const existing = result.get(resource) ?? [];
      existing.push(perm as Permission);
      result.set(resource, existing);
    }

    return result;
  }
}

export const permissionRegistry = new PermissionRegistry();

export function checkPermission(perm: Permission): boolean {
  const [resource] = perm.split(':') as [string, string];

  if (actorHasPermission(perm)) {
    return true;
  }

  // Check wildcard for resource (e.g., invoices:*)
  if (actorHasPermission(`${resource}:*`)) {
    return true;
  }

  // Check super admin wildcard
  if (actorHasPermission('*:*')) {
    return true;
  }

  return false;
}

export function requirePermission(perm: Permission): void {
  if (!checkPermission(perm)) {
    const actor = getActor();
    throw new AuthorizationError(
      `Permission denied: ${perm}. Actor ${actor?.id ?? 'unknown'} lacks required permission.`,
    );
  }
}

export function checkAnyPermission(perms: Permission[]): boolean {
  return perms.some(checkPermission);
}

export function checkAllPermissions(perms: Permission[]): boolean {
  return perms.every(checkPermission);
}

export function requireAnyPermission(perms: Permission[]): void {
  if (!checkAnyPermission(perms)) {
    throw new AuthorizationError(`Permission denied: requires one of [${perms.join(', ')}]`);
  }
}

export function requireAllPermissions(perms: Permission[]): void {
  if (!checkAllPermissions(perms)) {
    throw new AuthorizationError(`Permission denied: requires all of [${perms.join(', ')}]`);
  }
}
