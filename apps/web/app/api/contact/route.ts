import { NextResponse, type NextRequest } from 'next/server';
import { createTranslator } from 'next-intl';
import bn from '@/messages/bn.json';
import en from '@/messages/en.json';
import { clientIp, edgeHeaders } from '@/lib/http';

const API_URL = process.env.API_URL ?? 'http://localhost:4000';
const MAX_BODY = 8 * 1024;

type Json = { ok: true } | { ok: false; error: string };

function reply(body: Json, status: number) {
  return NextResponse.json(body, { status, headers: { 'Cache-Control': 'no-store' } });
}

/** The origin the browser used to reach us (behind a proxy: X-Forwarded-Host/Proto). */
function expectedOrigins(req: NextRequest): Set<string> {
  const out = new Set<string>([req.nextUrl.origin]);
  const host = req.headers.get('x-forwarded-host')?.split(',')[0]?.trim() || req.headers.get('host');
  const proto = req.headers.get('x-forwarded-proto')?.split(',')[0]?.trim() || req.nextUrl.protocol.replace(/:$/, '');
  if (host) out.add(`${proto}://${host}`);
  if (process.env.NEXT_PUBLIC_SITE_URL) {
    try {
      out.add(new URL(process.env.NEXT_PUBLIC_SITE_URL).origin);
    } catch {
      /* ignore a malformed setting */
    }
  }
  return out;
}

/** Error messages in the form's language (`?locale=en`; Bangla by default). */
function translator(req: NextRequest) {
  const locale = req.nextUrl.searchParams.get('locale') === 'en' ? 'en' : 'bn';
  return createTranslator({ locale, messages: locale === 'en' ? en : bn, namespace: 'ContactApi' });
}

function apiError(t: ReturnType<typeof translator>, status: number, detail: string): string {
  if (status === 429) return t('rateLimited');
  if (/subject.*required/i.test(detail)) return t('subjectRequired');
  if (/subject.*at least/i.test(detail)) return t('subjectMin');
  if (/subject.*at most/i.test(detail)) return t('subjectMax');
  if (/message.*required/i.test(detail)) return t('messageRequired');
  if (/message.*at least/i.test(detail)) return t('messageMin');
  if (/message.*at most/i.test(detail)) return t('messageMax');
  if (/email/i.test(detail)) return t('emailInvalid');
  if (/must be text|JSON/i.test(detail)) return t('unreadable');
  if (status >= 500) return t('serverError');
  return t('failed');
}

const str = (v: unknown) => (typeof v === 'string' ? v : undefined);

/** Same-origin proxy for the contact form → POST {API_URL}/v1/contact. Always answers JSON. */
export async function POST(req: NextRequest) {
  const t = translator(req);
  // CSRF: browsers always send Origin on a cross-site POST; require it and require it to be ours.
  const origin = req.headers.get('origin');
  if (!origin || !expectedOrigins(req).has(origin)) return reply({ ok: false, error: t('crossOrigin') }, 403);
  if (!(req.headers.get('content-type') ?? '').toLowerCase().startsWith('application/json')) {
    return reply({ ok: false, error: t('badType') }, 415);
  }

  let input: Record<string, unknown>;
  try {
    const text = await req.text();
    if (text.length > MAX_BODY) return reply({ ok: false, error: t('tooLarge') }, 413);
    const parsed: unknown = JSON.parse(text);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('not an object');
    input = parsed as Record<string, unknown>;
  } catch {
    return reply({ ok: false, error: t('unreadable') }, 400);
  }

  // Forward only the known fields; the API does the real validation.
  const payload = { subject: str(input.subject), message: str(input.message), email: str(input.email) || undefined, website: str(input.website) };
  const headers: Record<string, string> = { 'content-type': 'application/json', accept: 'application/json' };
  const ip = clientIp(req);
  if (ip) Object.assign(headers, edgeHeaders(ip));
  const requestId = req.headers.get('x-request-id');
  if (requestId && /^[A-Za-z0-9._-]{8,64}$/.test(requestId)) headers['x-request-id'] = requestId;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/v1/contact`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    return reply({ ok: false, error: t('unreachable') }, 502);
  }

  if (res.ok) return reply({ ok: true }, res.status === 201 ? 201 : 200);

  let detail = '';
  try {
    const problem = (await res.json()) as { detail?: unknown };
    if (typeof problem.detail === 'string') detail = problem.detail;
  } catch {
    /* not JSON: keep the generic message */
  }
  const status = res.status >= 500 ? 502 : res.status;
  return reply({ ok: false, error: apiError(t, res.status, detail) }, status);
}
