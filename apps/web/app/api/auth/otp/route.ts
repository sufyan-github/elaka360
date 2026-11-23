import type { NextRequest } from 'next/server';
import { clientIp, forward, problem, relay, sameOrigin } from '@/lib/http';

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return problem(403, 'Forbidden', 'cross-site request');
  const body = await req.json().catch(() => null);
  // email sign-in (Cloudflare deployment, apps/edge-api) or SMS (full API)
  const email = typeof body?.email === 'string';
  return relay(await forward(email ? '/v1/auth/email/request' : '/v1/auth/otp/request', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(email ? { email: body.email } : { phone: body?.phone }), ip: clientIp(req),
  }));
}
