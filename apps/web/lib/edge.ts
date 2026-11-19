import 'server-only';
import { getCloudflareContext } from '@opennextjs/cloudflare';

interface Fetcher { fetch(input: Request | string, init?: RequestInit): Promise<Response> }

/** The API Worker's service binding when running on Cloudflare (wrangler.jsonc → services: API); null elsewhere. */
function binding(): Fetcher | null {
  try {
    return (getCloudflareContext().env as { API?: Fetcher }).API ?? null;
  } catch {
    return null;   // next dev / next start / build time: no Cloudflare context
  }
}

/**
 * fetch() to the API. On Cloudflare the call goes through the service binding (a Worker cannot reliably fetch
 * another Worker on the same zone over its public hostname, and the binding skips the network); elsewhere it is
 * a normal fetch to `url` (API_URL).
 */
export function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const api = binding();
  if (!api) return fetch(url, init);
  const { next: _next, ...rest } = init as RequestInit & { next?: unknown };   // Next.js-only option
  return api.fetch(new Request(url, rest));
}
