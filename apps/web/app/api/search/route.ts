import { NextResponse, type NextRequest } from 'next/server';
import { forward } from '@/lib/http';

/** Search for the /search page: forwards to the API's /v1/search (Typesense/Postgres, or SQLite FTS on the edge). */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const q = (sp.get('q') ?? '').trim().slice(0, 80);
  if (q.length < 2) return NextResponse.json({ engine: 'none', areas: [], places: [] });
  const type = sp.get('type');
  const qs = new URLSearchParams({ q, limit: '20', ...(type === 'area' || type === 'place' ? { type } : {}) });
  const res = await forward(`/v1/search?${qs}`);
  if (!res.ok) {
    return NextResponse.json({ type: 'about:blank', title: 'Bad Gateway', status: 502, detail: 'search failed' },
      { status: 502, headers: { 'content-type': 'application/problem+json', 'cache-control': 'no-store' } });
  }
  return new NextResponse(await res.text(), { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=60' } });
}
