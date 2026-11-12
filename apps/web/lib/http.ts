import 'server-only';
import { NextResponse, type NextRequest } from 'next/server';
import type { AuthTokens } from '@elaka360/shared';
import { API_URL } from './api';

const TIMEOUT_MS = Number(process.env.API_TIMEOUT_MS ?? 5000);
export const AT_COOKIE = 'e360_at';
export const RT_COOKIE = 'e360_rt';
const secure = process.env.NODE_ENV === 'production';

/** CSRF guard for state-changing route handlers: the Origin must be this site. */
export function sameOrigin(req: NextRequest): boolean {
  const origin = req.headers.get('origin');
  if (!origin) return false;
  const allowed = new Set([req.nextUrl.origin, process.env.NEXT_PUBLIC_SITE_URL].filter(Boolean));
  return allowed.has(origin);
}

export function problem(status: number, title: string, detail?: string) {
  return NextResponse.json({ type: 'about:blank', title, status, ...(detail ? { detail } : {}) },
    { status, headers: { 'content-type': 'application/problem+json', 'cache-control': 'no-store' } });
}

/** Client-IP headers for the API: plain X-Forwarded-For, plus the signed edge headers when EDGE_SHARED_SECRET is set. */
export function edgeHeaders(ip: string): Record<string, string> {
  const secret = process.env.EDGE_SHARED_SECRET;
  return { 'X-Forwarded-For': ip, ...(secret ? { 'X-Edge-Client-IP': ip, 'X-Edge-Key': secret } : {}) };
}

/** Forward a request to the API; never throws (returns a 502 problem when the API is unreachable). */
export async function forward(path: string, init: RequestInit & { ip?: string | null } = {}): Promise<Response> {
  const { ip, ...rest } = init;
  try {
    return await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: { ...(rest.headers as Record<string, string>), ...(ip ? edgeHeaders(ip) : {}) },
      cache: 'no-store',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    return new Response(JSON.stringify({ type: 'about:blank', title: 'Bad Gateway', status: 502, detail: 'API unreachable' }),
      { status: 502, headers: { 'content-type': 'application/problem+json' } });
  }
}

/** Pass an API response through as JSON with no caching. */
export async function relay(res: Response) {
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') ?? 'application/json', 'cache-control': 'no-store' },
  });
}

/**
 * Client address to pass on to the API: X-Real-IP when our proxy sets it, else the LAST X-Forwarded-For entry
 * (the one our own reverse proxy appended; earlier entries are client-supplied and spoofable).
 */
export function clientIp(req: NextRequest): string | null {
  // On Cloudflare Workers (TRUST_CF_CONNECTING_IP=1) the edge sets CF-Connecting-IP; clients cannot forge it there.
  const cf = process.env.TRUST_CF_CONNECTING_IP === '1' ? req.headers.get('cf-connecting-ip')?.trim() : undefined;
  if (cf && /^[0-9a-fA-F:.]{2,45}$/.test(cf)) return cf;
  const real = req.headers.get('x-real-ip')?.trim();
  const xff = req.headers.get('x-forwarded-for')?.split(',').map((s) => s.trim()).filter(Boolean);
  const ip = real || xff?.[xff.length - 1] || null;
  return ip && /^[0-9a-fA-F:.]{2,45}$/.test(ip) ? ip : null;
}

export function setSession(res: NextResponse, t: Pick<AuthTokens, 'access_token' | 'refresh_token' | 'expires_in'>) {
  res.cookies.set(AT_COOKIE, t.access_token, { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: t.expires_in });
  if (t.refresh_token) res.cookies.set(RT_COOKIE, t.refresh_token, { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: 30 * 86400 });
}

export function clearSession(res: NextResponse) {
  res.cookies.set(AT_COOKIE, '', { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: 0 });
  res.cookies.set(RT_COOKIE, '', { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: 0 });
}
