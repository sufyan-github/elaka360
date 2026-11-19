import type { UserRole } from '@elaka360/shared';

export const PERMISSIONS = [
  'stats.read',
  'areas.read', 'areas.edit', 'areas.verify',
  'places.read', 'places.edit', 'places.verify',
  'sources.read', 'sources.edit',
  'contributions.moderate', 'reviews.moderate',
  'audit.read', 'users.manage',
] as const;
export type Permission = (typeof PERMISSIONS)[number];

const READ: Permission[] = ['stats.read', 'areas.read', 'places.read', 'sources.read'];

/**
 * Role → permissions. Staff roles map to the plan's titles:
 * super_admin = Super Admin, national_admin = Administrator, data_admin = Data Manager,
 * verifier = Geographic Verifier, moderator = Place Moderator, content_manager = Content Manager,
 * analyst = Analyst, readonly_staff = Read-only Staff.
 */
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  user: [],
  contributor: [],
  readonly_staff: READ,
  analyst: [...READ, 'audit.read'],
  content_manager: ['stats.read'],
  verifier: [...READ, 'areas.verify', 'places.verify'],
  moderator: [...READ, 'places.edit', 'contributions.moderate', 'reviews.moderate'],
  data_admin: [...READ, 'areas.edit', 'areas.verify', 'places.edit', 'places.verify', 'sources.edit', 'contributions.moderate', 'reviews.moderate', 'audit.read'],
  national_admin: [...PERMISSIONS],
  super_admin: [...PERMISSIONS],
};

export const STAFF_ROLES: UserRole[] = ['readonly_staff', 'analyst', 'content_manager', 'verifier', 'moderator', 'data_admin', 'national_admin', 'super_admin'];

export function can(role: UserRole, p: Permission): boolean {
  return ROLE_PERMISSIONS[role]?.includes(p) ?? false;
}

/** Which roles a manager may assign. Only a super admin can create another super admin. */
export function assignableRoles(managerRole: UserRole): UserRole[] {
  if (managerRole === 'super_admin') return ['user', 'contributor', ...STAFF_ROLES];
  if (managerRole === 'national_admin') return ['user', 'contributor', ...STAFF_ROLES.filter((r) => r !== 'super_admin' && r !== 'national_admin')];
  return [];
}
