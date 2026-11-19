import { NextResponse, type NextRequest } from 'next/server';
import { ACCESS_COOKIE, PATH_HEADER } from './lib/config';

/** Seconds before expiry at which we proactively renew, so forms are not submitted with a dying token. */
const RENEW_BEFORE_S = 90;

/** Read the `exp` claim without verifying (routing only; the API verifies every token). */
function expiresAt(jwt: string): number | null {
  const part = jwt.split('.')[1];
  if (!part) return null;
  try {
    const json = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
    const exp = (JSON.parse(json) as { exp?: unknown }).exp;
    return typeof exp === 'number' ? exp : null;
  } catch {
    return null;
  }
}

/**
 * Every page needs a session. The refresh cookie is scoped to /api, so pages cannot see it:
 * with no (or an expiring) access cookie we bounce through /api/auth/refresh, which renews the
 * session or sends the browser to /login.
 */
export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const at = req.cookies.get(ACCESS_COOKIE)?.value;
  const exp = at ? expiresAt(at) : null;
  const fresh = exp !== null && exp - Date.now() / 1000 > RENEW_BEFORE_S;

  if (!fresh && req.method === 'GET') {
    const url = req.nextUrl.clone();
    url.pathname = '/api/auth/refresh';
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  if (!at) {
    // A non-GET (server action) without any session: nothing to act as.
    return new NextResponse('sign in required', { status: 401 });
  }

  const h = new Headers(req.headers);
  h.set(PATH_HEADER, pathname + search);
  return NextResponse.next({ request: { headers: h } });
}

export const config = {
  matcher: ['/((?!api/|login|_next/static|_next/image|favicon\\.ico|icon\\.svg|robots\\.txt).*)'],
};
