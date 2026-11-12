import { NextResponse, type NextRequest } from 'next/server';

const API_URL = process.env.API_URL ?? 'http://localhost:4000';
const AT = 'e360_at';
const RT = 'e360_rt';
/** Matched against the path without its locale prefix, so /en/me is protected like /me. */
const PROTECTED = [/^\/me(\/|$)/, /^\/saved(\/|$)/, /^\/contribute\/new/];
const secure = process.env.NODE_ENV === 'production';

/** Must match HEADER_LOCALE_NAME in next-intl: a fallback for server code that runs without setRequestLocale. */
const LOCALE_HEADER = 'X-NEXT-INTL-LOCALE';

function expiresSoon(token: string | undefined): boolean {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]!.replace(/-/g, '+').replace(/_/g, '/')));
    return typeof payload.exp !== 'number' || payload.exp * 1000 < Date.now() + 30_000;
  } catch {
    return true;
  }
}

/** Route handlers and files are not localized; everything else is a page under app/[locale]. */
function isPage(pathname: string): boolean {
  return !(pathname === '/api' || pathname.startsWith('/api/') || /\.[a-z0-9]+$/i.test(pathname));
}

/**
 * Keeps the session alive: when the access cookie is missing or about to expire and a refresh
 * cookie exists, rotate tokens once here (server components cannot set cookies).
 * Protected pages redirect to the sign-in page of their own language when there is no session.
 *
 * Locales: `/x` is Bangla (rewritten to app/[locale] by next.config.ts), `/en/x` English, and `/bn/x` redirects
 * to `/x`. Nothing here reads Accept-Language or sets a locale cookie, so a URL always renders the same language
 * and pages stay cacheable.
 */
export async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const page = isPage(pathname);
  const english = pathname === '/en' || pathname.startsWith('/en/');
  const bare = english ? pathname.slice(3) || '/' : pathname;
  const isProtected = page && PROTECTED.some((r) => r.test(bare));
  const loginUrl = () => new URL(`${english ? '/en' : ''}/login?next=${encodeURIComponent(pathname + search)}`, req.url);
  if (page && (pathname === '/bn' || pathname.startsWith('/bn/'))) {
    return NextResponse.redirect(new URL(`${pathname.slice(3) || '/'}${search}`, req.url));
  }
  const pass = () => {
    if (page) req.headers.set(LOCALE_HEADER, english ? 'en' : 'bn');
    return NextResponse.next({ request: { headers: req.headers } });
  };

  const at = req.cookies.get(AT)?.value;
  const rt = req.cookies.get(RT)?.value;

  if (rt && expiresSoon(at)) {
    try {
      const res = await fetch(`${API_URL}/v1/auth/refresh`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: rt }), signal: AbortSignal.timeout(4000),
      });
      if (res.ok) {
        const t = (await res.json()) as { access_token: string; refresh_token: string | null; expires_in: number };
        // Make the new token visible to this request's server components and route handlers
        // (the modified cookie header is forwarded by NextResponse.next).
        req.cookies.set(AT, t.access_token);
        const out = pass();
        out.cookies.set(AT, t.access_token, { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: t.expires_in });
        if (t.refresh_token) out.cookies.set(RT, t.refresh_token, { httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: 30 * 86400 });
        return out;
      }
      if (res.status === 401) {
        const out = isProtected ? NextResponse.redirect(loginUrl()) : pass();
        out.cookies.set(AT, '', { path: '/', maxAge: 0 });
        out.cookies.set(RT, '', { path: '/', maxAge: 0 });
        return out;
      }
    } catch {
      /* API unreachable: carry on; pages handle their own errors */
    }
  }
  if (isProtected && !at && !rt) return NextResponse.redirect(loginUrl());
  return pass();
}

export const config = {
  matcher: ['/((?!_next/|api/(?:nearby|places-geo|suggest|contact)|geo/|data/|icons/|sw\\.js|manifest\\.webmanifest|favicon).*)'],
};
