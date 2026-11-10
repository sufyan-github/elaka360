import { BadRequestException, HttpException, HttpStatus, Injectable, UnauthorizedException } from '@nestjs/common';
import type { AuthTokens, Me } from '@elaka360/shared';
import { Db, audit } from '../db/db.service';
import { ROLE_PERMISSIONS } from '../common/auth/permissions';
import {
  ACCESS_TTL_S, OTP_MAX_ATTEMPTS, OTP_TTL_S, REFRESH_TTL_S, newOtp, newRefreshToken, normalisePhone, otpHash,
  parseRefreshToken, safeEqualHex, signAccess,
} from '../common/auth/tokens';
import { smsFromEnv } from './sms';

export const ME_SQL = `
SELECT id::int, name, phone, email, role::text, points, level, home_area_id::int, scope_area_id::int, profile_public,
       to_char(created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at,
       to_char(deletion_requested_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS deletion_requested_at
FROM users WHERE id = $1`;

const OTP_PER_PHONE_15M = 3;

@Injectable()
export class AuthService {
  private readonly sms = smsFromEnv();

  constructor(private readonly db: Db) {}

  async requestOtp(rawPhone: unknown, ip: string | null) {
    const phone = normalisePhone(rawPhone);
    if (!phone) throw new BadRequestException('phone must be a Bangladeshi mobile number, e.g. 01712345678');
    const recent = await this.db.one<{ n: number }>(
      `SELECT count(*)::int AS n FROM otp_challenges WHERE phone = $1 AND created_at > now() - interval '15 minutes'`, [phone]);
    if ((recent?.n ?? 0) >= OTP_PER_PHONE_15M) throw new HttpException('too many codes requested; try again later', HttpStatus.TOO_MANY_REQUESTS);
    const code = newOtp();
    const sent = await this.sms.send(phone, `Elaka360 code: ${code}. Valid 5 minutes. Do not share it.`);
    await this.db.many(
      `INSERT INTO otp_challenges(phone, code_hash, expires_at, ip) VALUES ($1, $2, now() + make_interval(secs => $3), $4::inet)`,
      [phone, otpHash(phone, code), OTP_TTL_S, ip],
    );
    return { sent: true, expires_in: OTP_TTL_S, ...(sent.devCode ? { dev_code: sent.devCode } : {}) };
  }

  async verifyOtp(rawPhone: unknown, rawCode: unknown, rawName: unknown, userAgent: string | undefined): Promise<AuthTokens> {
    const phone = normalisePhone(rawPhone);
    const code = typeof rawCode === 'string' ? rawCode.replace(/[০-৯]/g, (d) => String('০১২৩৪৫৬৭৮৯'.indexOf(d))).trim() : '';
    if (!phone || !/^\d{6}$/.test(code)) throw new BadRequestException('phone and a 6-digit code are required');
    const name = typeof rawName === 'string' ? rawName.normalize('NFC').trim().slice(0, 80) : '';

    return this.db.tx(async (q) => {
      const ch = await q.one<{ id: number; code_hash: string; attempts: number }>(
        `SELECT id::int, code_hash, attempts FROM otp_challenges
         WHERE phone = $1 AND consumed_at IS NULL AND expires_at > now() ORDER BY created_at DESC LIMIT 1 FOR UPDATE`, [phone]);
      if (!ch || ch.attempts >= OTP_MAX_ATTEMPTS) throw new UnauthorizedException('code expired or too many attempts; request a new one');
      if (!safeEqualHex(ch.code_hash, otpHash(phone, code))) {
        await q.many('UPDATE otp_challenges SET attempts = attempts + 1 WHERE id = $1', [ch.id]);
        throw new UnauthorizedException('wrong code');
      }
      await q.many('UPDATE otp_challenges SET consumed_at = now() WHERE id = $1', [ch.id]);
      let user = await q.one<{ id: number; role: string; status: string }>('SELECT id::int, role::text, status FROM users WHERE phone = $1', [phone]);
      if (user && user.status !== 'active') throw new UnauthorizedException('account is not active');
      if (!user) {
        user = await q.one<{ id: number; role: string; status: string }>(
          `INSERT INTO users(name, phone) VALUES ($1, $2) RETURNING id::int, role::text, status`, [name || 'ব্যবহারকারী', phone]);
        await audit(q, { actor: user!.id, action: 'user.register', entity: 'user', entityId: user!.id });
      }
      await q.many('UPDATE users SET last_login_at = now() WHERE id = $1', [user!.id]);
      const rt = newRefreshToken();
      await q.many(
        `INSERT INTO sessions(id, user_id, refresh_hash, user_agent, expires_at) VALUES ($1, $2, $3, $4, now() + make_interval(secs => $5))`,
        [rt.sessionId, user!.id, rt.hash, (userAgent ?? '').slice(0, 200), REFRESH_TTL_S]);
      return this.tokens(q, user!.id, user!.role, rt.sessionId, rt.token);
    });
  }

  /** Rotate a refresh token. Re-use of an old token revokes the whole session (theft signal). */
  async refresh(raw: unknown): Promise<AuthTokens> {
    const parsed = typeof raw === 'string' ? parseRefreshToken(raw) : null;
    if (!parsed) throw new UnauthorizedException('invalid refresh token');
    const out = await this.db.tx(async (q) => {
      const s = await q.one<{ user_id: number; refresh_hash: string; role: string; status: string }>(
        `SELECT s.user_id::int, s.refresh_hash, u.role::text, u.status FROM sessions s JOIN users u ON u.id = s.user_id
         WHERE s.id = $1 AND s.revoked_at IS NULL AND s.expires_at > now() FOR UPDATE OF s`, [parsed.sessionId]);
      if (!s || s.status !== 'active') throw new UnauthorizedException('session expired');
      if (!safeEqualHex(s.refresh_hash, parsed.hash)) {
        // Revoke in its own committed statement; throwing here would roll it back.
        await q.many('UPDATE sessions SET revoked_at = now() WHERE id = $1', [parsed.sessionId]);
        return 'reused' as const;
      }
      const rt = newRefreshToken(parsed.sessionId);
      await q.many('UPDATE sessions SET refresh_hash = $2, last_used_at = now() WHERE id = $1', [parsed.sessionId, rt.hash]);
      return this.tokens(q, s.user_id, s.role, parsed.sessionId, rt.token);
    });
    if (out === 'reused') throw new UnauthorizedException('refresh token reused; session revoked');
    return out;
  }

  async logout(sessionId: string, all: boolean, userId: number) {
    await this.db.many(all ? 'UPDATE sessions SET revoked_at = now() WHERE user_id = $1 AND revoked_at IS NULL'
                           : 'UPDATE sessions SET revoked_at = now() WHERE id = $2 AND user_id = $1', all ? [userId] : [userId, sessionId]);
    return { ok: true };
  }

  async me(userId: number, q = this.db as Pick<Db, 'one'>): Promise<Me> {
    const row = await q.one<Omit<Me, 'permissions'>>(ME_SQL, [userId]);
    if (!row) throw new UnauthorizedException('account not found');
    return { ...row, permissions: [...(ROLE_PERMISSIONS[row.role] ?? [])] };
  }

  private async tokens(q: Pick<Db, 'one'>, userId: number, role: string, sessionId: string, refresh: string): Promise<AuthTokens> {
    return { access_token: signAccess(userId, role, sessionId), refresh_token: refresh, expires_in: ACCESS_TTL_S, user: await this.me(userId, q) };
  }
}
