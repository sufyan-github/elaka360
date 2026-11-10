import { NextResponse, type NextRequest } from 'next/server';

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

/**
 * Client address to pass on. Our own reverse proxy appends the peer address as the LAST X-Forwarded-For
 * entry (anything before it is client-supplied and spoofable); X-Real-IP is used when the proxy sets it.
 */
function clientIp(req: NextRequest): string | null {
  const real = req.headers.get('x-real-ip')?.trim();
  const xff = req.headers.get('x-forwarded-for')?.split(',').map((s) => s.trim()).filter(Boolean);
  const ip = real || xff?.[xff.length - 1] || null;
  return ip && /^[0-9a-fA-F:.]{2,45}$/.test(ip) ? ip : null;
}

function bnError(status: number, detail: string): string {
  if (status === 429) return 'অনেকবার পাঠানো হয়েছে। এক মিনিট পরে আবার চেষ্টা করুন।';
  if (/subject.*required/i.test(detail)) return 'বিষয় লিখুন।';
  if (/subject.*at least/i.test(detail)) return 'বিষয় অন্তত ৩ অক্ষরের হতে হবে।';
  if (/subject.*at most/i.test(detail)) return 'বিষয় সর্বোচ্চ ১২০ অক্ষরের হতে পারে।';
  if (/message.*required/i.test(detail)) return 'বার্তা লিখুন।';
  if (/message.*at least/i.test(detail)) return 'বার্তা অন্তত ১০ অক্ষরের হতে হবে।';
  if (/message.*at most/i.test(detail)) return 'বার্তা সর্বোচ্চ ১০০০ অক্ষরের হতে পারে।';
  if (/email/i.test(detail)) return 'ইমেইল ঠিকানাটি সঠিক মনে হচ্ছে না।';
  if (/must be text|JSON/i.test(detail)) return 'ফর্মের তথ্য পড়া যায়নি। পাতাটি আবার লোড করে চেষ্টা করুন।';
  if (status >= 500) return 'সার্ভারে সমস্যা হয়েছে। কিছুক্ষণ পরে আবার চেষ্টা করুন।';
  return 'বার্তা পাঠানো যায়নি। তথ্যগুলো দেখে আবার চেষ্টা করুন।';
}

const str = (v: unknown) => (typeof v === 'string' ? v : undefined);

/** Same-origin proxy for the contact form → POST {API_URL}/v1/contact. Always answers JSON. */
export async function POST(req: NextRequest) {
  // CSRF: browsers always send Origin on a cross-site POST; require it and require it to be ours.
  const origin = req.headers.get('origin');
  if (!origin || !expectedOrigins(req).has(origin)) return reply({ ok: false, error: 'অনুরোধটি গ্রহণ করা যায়নি (ভিন্ন উৎস)।' }, 403);
  if (!(req.headers.get('content-type') ?? '').toLowerCase().startsWith('application/json')) {
    return reply({ ok: false, error: 'অনুরোধের ধরন সঠিক নয়।' }, 415);
  }

  let input: Record<string, unknown>;
  try {
    const text = await req.text();
    if (text.length > MAX_BODY) return reply({ ok: false, error: 'বার্তাটি অনেক বড়।' }, 413);
    const parsed: unknown = JSON.parse(text);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('not an object');
    input = parsed as Record<string, unknown>;
  } catch {
    return reply({ ok: false, error: 'ফর্মের তথ্য পড়া যায়নি। পাতাটি আবার লোড করে চেষ্টা করুন।' }, 400);
  }

  // Forward only the known fields; the API does the real validation.
  const payload = { subject: str(input.subject), message: str(input.message), email: str(input.email) || undefined, website: str(input.website) };
  const headers: Record<string, string> = { 'content-type': 'application/json', accept: 'application/json' };
  const ip = clientIp(req);
  if (ip) headers['x-forwarded-for'] = ip;
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
    return reply({ ok: false, error: 'এই মুহূর্তে সার্ভারের সঙ্গে যোগাযোগ করা যাচ্ছে না। কিছুক্ষণ পরে আবার চেষ্টা করুন।' }, 502);
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
  return reply({ ok: false, error: bnError(res.status, detail) }, status);
}
