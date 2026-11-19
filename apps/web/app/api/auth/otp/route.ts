import type { NextRequest } from 'next/server';
import { clientIp, forward, problem, relay, sameOrigin } from '@/lib/http';

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return problem(403, 'Forbidden', 'cross-site request');
  const body = await req.json().catch(() => null);
  return relay(await forward('/v1/auth/otp/request', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: body?.phone }), ip: clientIp(req),
  }));
}
