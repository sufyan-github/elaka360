import { CanActivate, ExecutionContext, ForbiddenException, Injectable, SetMetadata, UnauthorizedException, createParamDecorator } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { Request } from 'express';
import type { UserRole } from '@elaka360/shared';
import { Db } from '../../db/db.service';
import { verifyAccess } from './tokens';
import { can, type Permission } from './permissions';
import { STAFF_REQUIRE_2FA } from './totp';

export interface AuthUser {
  id: number;
  role: UserRole;
  name: string;
  session_id: string;
  scope_area_id: number | null;
  scope_path: string | null;
  mfa_enabled: boolean;
  mfa_verified: boolean;
}

export type AuthedRequest = Request & { id?: string; user?: AuthUser };

const AUTH_KEY = 'elaka360:auth';
/** Require a signed-in user; optionally a permission. */
export const RequireAuth = (permission?: Permission) => SetMetadata(AUTH_KEY, { permission: permission ?? null });
export const CurrentUser = createParamDecorator((_: unknown, ctx: ExecutionContext) => ctx.switchToHttp().getRequest<AuthedRequest>().user);

const USER_SQL = `
SELECT u.id::int, u.role::text, u.name, u.status, u.scope_area_id::int, a.path AS scope_path,
       u.totp_enabled_at IS NOT NULL AS mfa_enabled, s.mfa_at IS NOT NULL AS mfa_verified
FROM sessions s JOIN users u ON u.id = s.user_id LEFT JOIN admin_areas a ON a.id = u.scope_area_id
WHERE s.id = $1 AND s.user_id = $2 AND s.revoked_at IS NULL AND s.expires_at > now()`;

/**
 * Global guard. Reads a bearer token when present (so public routes can personalise),
 * and enforces @RequireAuth(permission) where declared. Sessions are checked on every
 * request, so logout and suspension take effect immediately.
 */
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private readonly reflector: Reflector, private readonly db: Db) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest<AuthedRequest>();
    const meta = this.reflector.getAllAndOverride<{ permission: Permission | null } | undefined>(AUTH_KEY, [ctx.getHandler(), ctx.getClass()]);
    const header = req.header('authorization');
    if (header?.startsWith('Bearer ')) {
      const claims = verifyAccess(header.slice(7).trim());
      if (claims) {
        const row = await this.db.one<{ id: number; role: UserRole; name: string; status: string; scope_area_id: number | null; scope_path: string | null; mfa_enabled: boolean; mfa_verified: boolean }>(
          USER_SQL, [claims.sid, Number(claims.sub)]);
        if (row && row.status === 'active') {
          req.user = { id: row.id, role: row.role, name: row.name, session_id: claims.sid, scope_area_id: row.scope_area_id, scope_path: row.scope_path,
                       mfa_enabled: row.mfa_enabled, mfa_verified: row.mfa_verified };
        }
      }
    }
    if (!meta) return true;
    if (!req.user) throw new UnauthorizedException('sign in required');
    if (meta.permission && !can(req.user.role, meta.permission)) throw new ForbiddenException('not allowed for your role');
    // Staff actions need a session that passed two-factor authentication (when STAFF_REQUIRE_2FA is on).
    if (meta.permission && STAFF_REQUIRE_2FA && !req.user.mfa_verified) {
      throw new ForbiddenException(req.user.mfa_enabled
        ? { type: 'urn:elaka360:mfa-required', message: 'enter your authenticator code to continue' }
        : { type: 'urn:elaka360:mfa-enrollment-required', message: 'set up two-factor authentication to use staff features' });
    }
    return true;
  }
}

/** Staff with a geographic scope may only act on records whose area path lies under it. */
export function assertInScope(user: AuthUser, targetPath: string | null | undefined) {
  if (!user.scope_path) return;
  if (!targetPath || !(targetPath === user.scope_path || targetPath.startsWith(`${user.scope_path}/`))) {
    throw new ForbiddenException('outside your assigned area');
  }
}
