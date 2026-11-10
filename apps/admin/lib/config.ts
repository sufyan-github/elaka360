/** Shared constants (safe for middleware, server and client code — no secrets here). */

export const ACCESS_COOKIE = 'e360a_at';
export const REFRESH_COOKIE = 'e360a_rt';
/** The refresh cookie is only ever sent to the BFF route handlers. */
export const REFRESH_COOKIE_PATH = '/api';
/** Fallback refresh lifetime when the API does not tell us (matches the API default of 30 days). */
export const REFRESH_MAX_AGE_S = 30 * 86400;

/** Header set by middleware so server code knows which page is being rendered (for redirects back after refresh). */
export const PATH_HEADER = 'x-e360a-path';

/** Only same-site relative paths are allowed as post-login / post-refresh targets. */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\') || next.startsWith('/api/')) return '/';
  return next;
}
