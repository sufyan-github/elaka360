import { NextResponse, type NextRequest } from 'next/server';
import { ACCESS_COOKIE, REFRESH_COOKIE } from '@/lib/config';
import { isSameOrigin } from '@/lib/csrf';
import { apiFetchRaw, clearAuthCookies, refreshTokens } from '@/lib/session';
import { forbidden } from '../util';

/** Revoke the API session (renewing first if the access token has lapsed), then clear cookies. */
export async function POST(req: NextRequest) {
  if (!isSameOrigin(req.headers)) return forbidden();
  const logout = (token: string) =>
    apiFetchRaw('/v1/auth/logout', { method: 'POST', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' }, body: '{}' })
      .then((r) => r.status);
  const at = req.cookies.get(ACCESS_COOKIE)?.value;
  let status = at ? await logout(at) : 401;
  if (status === 401) {
    const rt = req.cookies.get(REFRESH_COOKIE)?.value;
    const fresh = rt ? await refreshTokens(rt) : null;
    if (fresh?.ok) status = await logout(fresh.tokens.access_token);
  }
  const res = NextResponse.redirect(new URL('/login', req.nextUrl), 303);
  clearAuthCookies(res.cookies);
  return res;
}
