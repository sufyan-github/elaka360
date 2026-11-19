import { NextResponse, type NextRequest } from 'next/server';
import { isSameOrigin } from '@/lib/csrf';
import { apiFetchRaw } from '@/lib/session';
import { forbidden, readJson, relay } from '../../util';

export async function POST(req: NextRequest) {
  if (!isSameOrigin(req.headers)) return forbidden();
  const b = await readJson(req);
  const res = await apiFetchRaw('/v1/auth/otp/request', {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ phone: b.phone }),
  });
  if (!res.ok) return relay(res);
  const data = (await res.json()) as { sent: boolean; expires_in: number; dev_code?: string };
  // dev_code exists only when the API runs with SMS_PROVIDER=dev; pass it through as-is.
  return NextResponse.json({ sent: data.sent, expires_in: data.expires_in, ...(data.dev_code ? { dev_code: data.dev_code } : {}) });
}
