import { NextResponse, type NextRequest } from 'next/server';
import type { AuthTokens } from '@elaka360/shared';
import { isSameOrigin } from '@/lib/csrf';
import { apiFetchRaw, setAuthCookies } from '@/lib/session';
import { forbidden, readJson, relay } from '../../util';

export async function POST(req: NextRequest) {
  if (!isSameOrigin(req.headers)) return forbidden();
  const b = await readJson(req);
  const res = await apiFetchRaw('/v1/auth/otp/verify', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'user-agent': `elaka360-admin; ${req.headers.get('user-agent') ?? ''}`.slice(0, 200) },
    body: JSON.stringify({ phone: b.phone, code: b.code }),
  });
  if (!res.ok) return relay(res);
  const t = (await res.json()) as AuthTokens;
  // Tokens go into httpOnly cookies only; the browser gets just what the UI needs.
  const out = NextResponse.json({ ok: true, staff: t.user.permissions.length > 0, name: t.user.name });
  setAuthCookies(out.cookies, t);
  return out;
}
