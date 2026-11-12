import { NextResponse, type NextRequest } from 'next/server';
import { AT_COOKIE, clearSession, forward, problem, sameOrigin } from '@/lib/http';

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return problem(403, 'Forbidden', 'cross-site request');
  const token = req.cookies.get(AT_COOKIE)?.value;
  const all = req.nextUrl.searchParams.get('all') === '1';
  if (token) await forward('/v1/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ all }) });
  const out = NextResponse.json({ ok: true }, { headers: { 'cache-control': 'no-store' } });
  clearSession(out);
  return out;
}
