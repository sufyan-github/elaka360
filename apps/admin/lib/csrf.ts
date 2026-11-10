import 'server-only';

/** The admin's own origin: ADMIN_ORIGIN in production, else derived from the request's Host. */
export function expectedOrigin(h: Headers): string | null {
  if (process.env.ADMIN_ORIGIN) return process.env.ADMIN_ORIGIN.replace(/\/$/, '');
  const host = h.get('x-forwarded-host') ?? h.get('host');
  if (!host) return null;
  const proto = h.get('x-forwarded-proto') ?? (process.env.NODE_ENV === 'production' ? 'https' : 'http');
  return `${proto.split(',')[0]!.trim()}://${host.split(',')[0]!.trim()}`;
}

/**
 * CSRF check for every state-changing request: the browser-set Origin header must equal the admin
 * origin, and Fetch Metadata (when sent) must say same-origin. Cookies are SameSite=Lax as well.
 */
export function isSameOrigin(h: Headers): boolean {
  const origin = h.get('origin');
  const expected = expectedOrigin(h);
  if (!origin || !expected || origin !== expected) return false;
  const site = h.get('sec-fetch-site');
  return !site || site === 'same-origin';
}
