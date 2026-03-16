export const AuditAction = {
  CREATE: 'CREATE',
  UPDATE: 'UPDATE',
  DELETE: 'DELETE',
  ARCHIVE: 'ARCHIVE',
  RESTORE: 'RESTORE',
  LOGIN: 'LOGIN',
  LOGOUT: 'LOGOUT',
  PERMISSION_CHANGE: 'PERMISSION_CHANGE',
  SETTING_CHANGE: 'SETTING_CHANGE',
  EXPORT: 'EXPORT',
  IMPORT: 'IMPORT',
  VIEW: 'VIEW',
} as const;

export type AuditActionType = (typeof AuditAction)[keyof typeof AuditAction];

export const AuditActorType = {
  USER: 'user',
  SYSTEM: 'system',
  SERVICE: 'service',
  ANONYMOUS: 'anonymous',
} as const;

export type AuditActorType = (typeof AuditActorType)[keyof typeof AuditActorType];
