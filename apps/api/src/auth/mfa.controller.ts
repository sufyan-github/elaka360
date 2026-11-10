import { BadRequestException, Body, ConflictException, Controller, HttpCode, Post, Req, UnauthorizedException } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Throttle } from '@nestjs/throttler';
import { Db, audit, type Queryable } from '../db/db.service';
import { CurrentUser, RequireAuth, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { body } from '../common/params';
import { decryptSecret, encryptSecret, hashRecovery, newRecoveryCodes, newTotpSecret, otpauthUri, verifyTotp } from '../common/auth/totp';
import { scaled } from '../common/throttle';

const MAX_FAILURES = 10;

function codeOf(raw: unknown): string {
  const c = body(raw).code;
  if (typeof c !== 'string' || !c.trim()) throw new BadRequestException('code is required');
  return c.replace(/[০-৯]/g, (d) => String('০১২৩৪৫৬৭৮৯'.indexOf(d))).replace(/\s/g, '').toLowerCase();
}

@ApiTags('auth')
@Controller('v1')
@RequireAuth()
export class MfaController {
  constructor(private readonly db: Db) {}

  @Post('me/2fa/setup')
  @HttpCode(200)
  @ApiOperation({ summary: 'Start authenticator (TOTP) setup: returns the secret and an otpauth:// URI' })
  async setup(@CurrentUser() u: AuthUser) {
    if (u.mfa_enabled) throw new ConflictException('two-factor authentication is already on');
    const secret = newTotpSecret();
    const row = await this.db.one<{ phone: string | null }>(
      'UPDATE users SET totp_pending_enc = $2 WHERE id = $1 RETURNING phone', [u.id, encryptSecret(secret)]);
    return { secret, otpauth_uri: otpauthUri(secret, row?.phone ?? `user-${u.id}`) };
  }

  @Post('me/2fa/enable')
  @HttpCode(200)
  @Throttle({ default: { limit: scaled(10), ttl: 60_000 } })
  @ApiOperation({ summary: 'Confirm setup with a current code; returns 8 one-time recovery codes (shown once)' })
  async enable(@CurrentUser() u: AuthUser, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const code = codeOf(raw);
    return this.db.tx(async (q) => {
      const row = await q.one<{ pending: string | null; enabled: boolean }>(
        'SELECT totp_pending_enc AS pending, totp_enabled_at IS NOT NULL AS enabled FROM users WHERE id = $1 FOR UPDATE', [u.id]);
      if (row?.enabled) throw new ConflictException('two-factor authentication is already on');
      if (!row?.pending) throw new BadRequestException('start setup first');
      const step = verifyTotp(decryptSecret(row.pending), code, null);
      if (step === null) throw new UnauthorizedException('wrong code');
      const codes = newRecoveryCodes();
      await q.many(
        `UPDATE users SET totp_secret_enc = totp_pending_enc, totp_pending_enc = NULL, totp_enabled_at = now(),
           totp_last_step = $2, recovery_hashes = $3 WHERE id = $1`, [u.id, step, codes.map(hashRecovery)]);
      await q.many('UPDATE sessions SET mfa_at = now(), mfa_failures = 0 WHERE id = $1', [u.session_id]);
      await audit(q, { actor: u.id, action: 'user.2fa_enabled', entity: 'user', entityId: u.id, requestId: req.id, ip: req.ip });
      return { enabled: true, recovery_codes: codes };
    });
  }

  @Post('auth/2fa/verify')
  @HttpCode(200)
  @Throttle({ default: { limit: scaled(10), ttl: 60_000 } })
  @ApiOperation({ summary: 'Pass 2FA for this session with an authenticator code or a recovery code' })
  async verify(@CurrentUser() u: AuthUser, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const code = codeOf(raw);
    const out = await this.db.tx(async (q) => {
      if (!(await this.check(q, u.id, code))) {
        const s = await q.one<{ f: number }>('UPDATE sessions SET mfa_failures = mfa_failures + 1 WHERE id = $1 RETURNING mfa_failures AS f', [u.session_id]);
        if ((s?.f ?? 0) >= MAX_FAILURES) await q.many('UPDATE sessions SET revoked_at = now() WHERE id = $1', [u.session_id]);
        return 'fail' as const;
      }
      await q.many('UPDATE sessions SET mfa_at = now(), mfa_failures = 0 WHERE id = $1', [u.session_id]);
      await audit(q, { actor: u.id, action: 'user.2fa_verified', entity: 'user', entityId: u.id, requestId: req.id, ip: req.ip });
      return 'ok' as const;
    });
    if (out === 'fail') throw new UnauthorizedException('wrong code');
    return { verified: true };
  }

  @Post('me/2fa/disable')
  @HttpCode(200)
  @Throttle({ default: { limit: scaled(5), ttl: 60_000 } })
  @ApiOperation({ summary: 'Turn 2FA off (needs a current or recovery code)' })
  async disable(@CurrentUser() u: AuthUser, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const code = codeOf(raw);
    return this.db.tx(async (q) => {
      if (!(await this.check(q, u.id, code))) throw new UnauthorizedException('wrong code');
      await q.many(`UPDATE users SET totp_secret_enc = NULL, totp_pending_enc = NULL, totp_enabled_at = NULL, totp_last_step = NULL,
                      recovery_hashes = '{}' WHERE id = $1`, [u.id]);
      await q.many('UPDATE sessions SET mfa_at = NULL WHERE user_id = $1', [u.id]);
      await audit(q, { actor: u.id, action: 'user.2fa_disabled', entity: 'user', entityId: u.id, requestId: req.id, ip: req.ip });
      return { enabled: false };
    });
  }

  /** TOTP (no reuse of an accepted step) or a recovery code (consumed). */
  private async check(q: Queryable, userId: number, code: string): Promise<boolean> {
    const row = await q.one<{ secret: string | null; last: string | null; hashes: string[] }>(
      'SELECT totp_secret_enc AS secret, totp_last_step::text AS last, recovery_hashes AS hashes FROM users WHERE id = $1 FOR UPDATE', [userId]);
    if (!row?.secret) throw new BadRequestException('two-factor authentication is not set up');
    const step = verifyTotp(decryptSecret(row.secret), code, row.last === null ? null : Number(row.last));
    if (step !== null) {
      await q.many('UPDATE users SET totp_last_step = $2 WHERE id = $1', [userId, step]);
      return true;
    }
    const h = hashRecovery(code);
    if (row.hashes.includes(h)) {
      await q.many('UPDATE users SET recovery_hashes = array_remove(recovery_hashes, $2) WHERE id = $1', [userId, h]);
      return true;
    }
    return false;
  }
}
