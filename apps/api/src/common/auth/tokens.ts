import { createHash, createHmac, randomBytes, randomInt, randomUUID, timingSafeEqual } from 'node:crypto';
import { Logger } from '@nestjs/common';

/** HS256 JWTs and opaque refresh tokens, built on node:crypto (no extra dependency). */

const log = new Logger('Auth');
let devSecret: string | null = null;

export function jwtSecret(): string {
  const s = process.env.AUTH_JWT_SECRET;
  if (s && s.length >= 32) return s;
  if (process.env.NODE_ENV === 'production') throw new Error('AUTH_JWT_SECRET (>= 32 chars) is required in production');
  if (!devSecret) {
    devSecret = randomBytes(32).toString('hex');
    log.warn('AUTH_JWT_SECRET not set: using a random per-process secret (development only).');
  }
  return devSecret;
}

const b64 = (b: Buffer | string) => Buffer.from(b).toString('base64url');

export interface AccessClaims {
  sub: string;   // user id
  role: string;
  sid: string;   // session id
  iat: number;
  exp: number;
}

export const ACCESS_TTL_S = Number(process.env.AUTH_ACCESS_TTL_S ?? 900);          // 15 min
export const REFRESH_TTL_S = Number(process.env.AUTH_REFRESH_TTL_S ?? 30 * 86400); // 30 days

export function signAccess(userId: number, role: string, sessionId: string, now = Math.floor(Date.now() / 1000)): string {
  const header = b64(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = b64(JSON.stringify({ sub: String(userId), role, sid: sessionId, iat: now, exp: now + ACCESS_TTL_S } satisfies AccessClaims));
  const sig = b64(createHmac('sha256', jwtSecret()).update(`${header}.${payload}`).digest());
  return `${header}.${payload}.${sig}`;
}

export function verifyAccess(token: string, now = Math.floor(Date.now() / 1000)): AccessClaims | null {
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [h, p, s] = parts as [string, string, string];
  const expected = createHmac('sha256', jwtSecret()).update(`${h}.${p}`).digest();
  const given = Buffer.from(s, 'base64url');
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) return null;
  try {
    const header = JSON.parse(Buffer.from(h, 'base64url').toString());
    if (header.alg !== 'HS256') return null;
    const claims = JSON.parse(Buffer.from(p, 'base64url').toString()) as AccessClaims;
    if (typeof claims.exp !== 'number' || claims.exp <= now) return null;
    return claims;
  } catch {
    return null;
  }
}

export const sha256 = (s: string) => createHash('sha256').update(s).digest('hex');

/** Refresh token = "<session uuid>.<secret>"; only sha256(secret) is stored. */
export function newRefreshToken(sessionId: string = randomUUID()) {
  const secret = randomBytes(32).toString('base64url');
  return { sessionId, token: `${sessionId}.${secret}`, hash: sha256(secret) };
}

export function parseRefreshToken(token: string): { sessionId: string; hash: string } | null {
  const m = /^([0-9a-f-]{36})\.([A-Za-z0-9_-]{40,60})$/.exec(token ?? '');
  return m ? { sessionId: m[1]!, hash: sha256(m[2]!) } : null;
}

export function safeEqualHex(a: string, b: string): boolean {
  const x = Buffer.from(a, 'hex');
  const y = Buffer.from(b, 'hex');
  return x.length === y.length && timingSafeEqual(x, y);
}

/* ---------- OTP ---------- */

export const OTP_TTL_S = 300;
export const OTP_MAX_ATTEMPTS = 5;

export function newOtp(): string {
  return String(randomInt(0, 1_000_000)).padStart(6, '0');
}

export function otpHash(phone: string, code: string): string {
  return createHmac('sha256', jwtSecret()).update(`otp:${phone}:${code}`).digest('hex');
}

/** "01712345678", "+8801712345678", "8801712345678" (ASCII or Bangla digits) → "+8801712345678". */
export function normalisePhone(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  const ascii = raw.replace(/[০-৯]/g, (d) => String('০১২৩৪৫৬৭৮৯'.indexOf(d))).replace(/[\s-]/g, '');
  const m = /^(?:\+?88)?(01[3-9]\d{8})$/.exec(ascii);
  return m ? `+88${m[1]}` : null;
}
