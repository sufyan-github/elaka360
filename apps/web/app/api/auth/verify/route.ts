import { NextResponse, type NextRequest } from 'next/server';
import type { AuthTokens } from '@elaka360/shared';
import { clientIp, forward, problem, relay, sameOrigin, setSession } from '@/lib/http';

/** Exchanges the code for tokens and keeps them in httpOnly cookies; the browser only sees the user. */
export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return problem(403, 'Forbidden', 'cross-site request');
  const body = await req.json().catch(() => null);
  const res = await forward('/v1/auth/otp/verify', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'User-Agent': req.headers.get('user-agent') ?? '' },
    body: JSON.stringify({ phone: body?.phone, code: body?.code, name: body?.name }), ip: clientIp(req),
  });
  if (!res.ok) return relay(res);
  const t = (await res.json()) as AuthTokens;
  const out = NextResponse.json({ user: t.user }, { headers: { 'cache-control': 'no-store' } });
  setSession(out, t);
  return out;
}
