import { NextResponse, type NextRequest } from 'next/server';
import { REFRESH_COOKIE, safeNext } from '@/lib/config';
import { UNREACHABLE, clearAuthCookies, refreshTokens, setAuthCookies } from '@/lib/session';

/**
 * Renew the session from the refresh cookie (only sent to /api/*), rotate both cookies and return
 * to `next`. Without a usable refresh token, clear cookies and go to /login.
 */
export async function GET(req: NextRequest) {
  const next = safeNext(req.nextUrl.searchParams.get('next'));
  const rt = req.cookies.get(REFRESH_COOKIE)?.value;
  const fresh = rt ? await refreshTokens(rt) : null;
  if (fresh && !fresh.ok && fresh.reason === 'unreachable') {
    // Keep the session: the API is down, not the token.
    return new NextResponse(
      `<!doctype html><html lang="bn"><meta charset="utf-8"><title>API unreachable</title><body style="font-family:system-ui;padding:2rem">
       <p>${UNREACHABLE.detail}</p><p><a href="${encodeURI(next)}">আবার চেষ্টা করুন · Retry</a></p></body></html>`,
      { status: 502, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } });
  }
  if (!fresh?.ok) {
    const login = new URL('/login', req.nextUrl);
    if (next !== '/') login.searchParams.set('next', next);
    const res = NextResponse.redirect(login, 303);
    clearAuthCookies(res.cookies);
    return res;
  }
  const res = NextResponse.redirect(new URL(next, req.nextUrl), 303);
  res.headers.set('cache-control', 'no-store');
  setAuthCookies(res.cookies, fresh.tokens);
  return res;
}
