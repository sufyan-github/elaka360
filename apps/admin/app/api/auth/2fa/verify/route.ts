import type { NextRequest } from 'next/server';
import { isSameOrigin } from '@/lib/csrf';
import { adminFetch } from '@/lib/api';
import { forbidden, readJson, relay } from '../../util';

/** Two-factor verify: forwarded to the API with the session cookie (Origin-checked). */
export async function POST(req: NextRequest) {
  if (!isSameOrigin(req.headers)) return forbidden();
  const b = await readJson(req);
  const res = await adminFetch('/v1/auth/2fa/verify', { method: 'POST', body: JSON.stringify(typeof b.code === 'string' ? { code: b.code } : {}) });
  return relay(res);
}
