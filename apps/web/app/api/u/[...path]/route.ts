import type { NextRequest } from 'next/server';
import { AT_COOKIE, clientIp, forward, problem, relay, sameOrigin } from '@/lib/http';

/**
 * Signed-in actions from client components (save, review, contribute, profile), forwarded to the API
 * with the session cookie as a bearer token. Only these API paths are reachable through it.
 */
const ALLOWED = [
  /^me(\/(saved(\/\d+)?|collections(\/\d+)?|reviews|contributions(\/stats)?|deletion-request))?$/,
  /^contributions(\/\d+(\/submit)?)?$/,
  /^places\/[a-z0-9-]{1,120}\/reviews$/,
  /^reviews\/\d+(\/report)?$/,
];

async function handle(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const path = (await params).path.join('/');
  if (!ALLOWED.some((r) => r.test(path))) return problem(404, 'Not Found');
  if (req.method !== 'GET' && !sameOrigin(req)) return problem(403, 'Forbidden', 'cross-site request');
  const token = req.cookies.get(AT_COOKIE)?.value;
  if (!token) return problem(401, 'Unauthorized', 'sign in required');
  const body = req.method === 'GET' || req.method === 'DELETE' ? undefined : await req.text();
  if (body && body.length > 20_000) return problem(413, 'Payload Too Large');
  return relay(await forward(`/v1/${path}${req.nextUrl.search}`, {
    method: req.method,
    headers: { Authorization: `Bearer ${token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body,
    ip: clientIp(req),
  }));
}

export { handle as GET, handle as POST, handle as PATCH, handle as DELETE };
