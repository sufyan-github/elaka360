import 'server-only';
import { createHash } from 'node:crypto';
import type { AuthTokens } from '@elaka360/shared';
import { ACCESS_COOKIE, REFRESH_COOKIE, REFRESH_COOKIE_PATH, REFRESH_MAX_AGE_S } from './config';

export const API_URL = process.env.API_URL ?? 'http://localhost:4000';

const secure = process.env.NODE_ENV === 'production';

/** Minimal shape shared by `cookies()` and `NextResponse.cookies`. */
interface CookieWriter {
  set(name: string, value: string, opts: Record<string, unknown>): unknown;
}

/**
 * Store the tokens. The API omits a new refresh token (`refresh_token: null`) when two refreshes
 * race with the same token; the existing refresh cookie is then still the valid one and is kept.
 */
export function setAuthCookies(jar: CookieWriter, t: Pick<AuthTokens, 'access_token' | 'refresh_token' | 'expires_in'>) {
  jar.set(ACCESS_COOKIE, t.access_token, {
    httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: Math.max(60, Number(t.expires_in) || 900),
  });
  if (typeof t.refresh_token === 'string' && t.refresh_token !== '') {
    jar.set(REFRESH_COOKIE, t.refresh_token, {
      httpOnly: true, secure, sameSite: 'lax', path: REFRESH_COOKIE_PATH, maxAge: REFRESH_MAX_AGE_S,
    });
  }
}

export function clearAuthCookies(jar: CookieWriter) {
  jar.set(ACCESS_COOKIE, '', { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: 0 });
  jar.set(REFRESH_COOKIE, '', { httpOnly: true, secure, sameSite: 'lax', path: REFRESH_COOKIE_PATH, maxAge: 0 });
}

export type RefreshResult = { ok: true; tokens: AuthTokens } | { ok: false; reason: 'invalid' | 'unreachable' };

/**
 * Refresh tokens rotate and re-use of an old one revokes the session. Several requests from one
 * browser can race to refresh with the same cookie (parallel tabs, prefetches), so concurrent and
 * recent refreshes of the same token share one API call (the API additionally tolerates a race
 * within 30 s by answering with `refresh_token: null`). In-process only: run a single admin
 * instance, or put sticky sessions in front of several.
 */
const inflight = new Map<string, { at: number; p: Promise<RefreshResult> }>();
const SHARE_MS = 30_000;

export function refreshTokens(refreshToken: string): Promise<RefreshResult> {
  const key = createHash('sha256').update(refreshToken).digest('hex');
  const now = Date.now();
  for (const [k, v] of inflight) if (now - v.at > SHARE_MS) inflight.delete(k);
  const hit = inflight.get(key);
  if (hit) return hit.p;
  const p = (async (): Promise<RefreshResult> => {
    let res: Response;
    try {
      res = await fetch(`${API_URL}/v1/auth/refresh`, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }), cache: 'no-store',
      });
    } catch {
      inflight.delete(key); // a network failure says nothing about the token; allow a retry
      return { ok: false, reason: 'unreachable' };
    }
    if (res.status >= 500) {
      inflight.delete(key);
      return { ok: false, reason: 'unreachable' };
    }
    if (!res.ok) return { ok: false, reason: 'invalid' };
    return { ok: true, tokens: (await res.json()) as AuthTokens };
  })();
  inflight.set(key, { at: now, p });
  return p;
}

/** Problem body for when the API cannot be reached. */
export const UNREACHABLE = { type: 'about:blank', title: 'Bad Gateway', status: 502, detail: 'API সার্ভারে পৌঁছানো যাচ্ছে না (API unreachable); একটু পরে আবার চেষ্টা করুন।' };

/**
 * The browser's IP as seen by this server: X-Real-IP from our proxy, else the last X-Forwarded-For entry
 * (the one our own proxy appended; earlier entries can be forged by the client). Null outside a request.
 */
async function clientIp(): Promise<string | null> {
  try {
    const { headers } = await import('next/headers');
    const h = await headers();
    return h.get('x-real-ip') || h.get('x-forwarded-for')?.split(',').at(-1)?.trim() || null;
  } catch {
    return null; // outside a request (e.g. build)
  }
}

/** fetch() to the API that turns a network failure into a 502 Response instead of throwing. */
export async function apiFetchRaw(path: string, init: RequestInit): Promise<Response> {
  try {
    // Forward the client IP so the API's per-IP limits apply to the person, not to this server.
    const ip = await clientIp();
    const h = new Headers(init.headers);
    if (ip && /^[0-9a-fA-F:.]{3,45}$/.test(ip)) h.set('x-forwarded-for', ip);
    return await fetch(`${API_URL}${path}`, { cache: 'no-store', ...init, headers: h, signal: init.signal ?? AbortSignal.timeout(8000) });
  } catch {
    return new Response(JSON.stringify(UNREACHABLE), { status: 502, headers: { 'content-type': 'application/problem+json' } });
  }
}
