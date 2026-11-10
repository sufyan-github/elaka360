import { NextResponse, type NextRequest } from 'next/server';

const API_URL = process.env.API_URL ?? 'http://localhost:4000';
const AT = 'e360_at';
const RT = 'e360_rt';
const PROTECTED = [/^\/me(\/|$)/, /^\/saved(\/|$)/, /^\/contribute\/new/];
const secure = process.env.NODE_ENV === 'production';

function expiresSoon(token: string | undefined): boolean {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]!.replace(/-/g, '+').replace(/_/g, '/')));
    return typeof payload.exp !== 'number' || payload.exp * 1000 < Date.now() + 30_000;
  } catch {
    return true;
  }
}

/**
 * Keeps the session alive: when the access cookie is missing or about to expire and a refresh
 * cookie exists, rotate tokens once here (server components cannot set cookies).
 * Protected pages redirect to /login when there is no session.
 */
export async function middleware(req: NextRequest) {
  const at = req.cookies.get(AT)?.value;
  const rt = req.cookies.get(RT)?.value;
  const isProtected = PROTECTED.some((r) => r.test(req.nextUrl.pathname));

  if (rt && expiresSoon(at)) {
    try {
      const res = await fetch(`${API_URL}/v1/auth/refresh`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: rt }), signal: AbortSignal.timeout(4000),
      });
      if (res.ok) {
        const t = (await res.json()) as { access_token: string; refresh_token: string | null; expires_in: number };
        // Make the new token visible to this request's server components and route handlers.
        req.cookies.set(AT, t.access_token);
        const out = NextResponse.next({ request: { headers: req.headers } });
        out.cookies.set(AT, t.access_token, { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: t.expires_in });
        if (t.refresh_token) out.cookies.set(RT, t.refresh_token, { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: 30 * 86400 });
        return out;
      }
      if (res.status === 401) {
        const out = isProtected ? NextResponse.redirect(new URL(`/login?next=${encodeURIComponent(req.nextUrl.pathname)}`, req.url)) : NextResponse.next();
        out.cookies.set(AT, '', { path: '/', maxAge: 0 });
        out.cookies.set(RT, '', { path: '/', maxAge: 0 });
        return out;
      }
    } catch {
      /* API unreachable: carry on; pages handle their own errors */
    }
  }
  if (isProtected && !at && !rt) {
    return NextResponse.redirect(new URL(`/login?next=${encodeURIComponent(req.nextUrl.pathname + req.nextUrl.search)}`, req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/|api/(?:nearby|places-geo|suggest|contact)|geo/|data/|icons/|sw\\.js|manifest\\.webmanifest|favicon).*)'],
};
