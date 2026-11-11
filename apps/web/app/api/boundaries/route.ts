import { NextResponse, type NextRequest } from 'next/server';
import { forward, problem, relay } from '@/lib/http';

/** Child-area boundaries for the live map (GeoJSON). Boundaries change rarely: cache for an hour. */
export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get('area_id') ?? '';
  const levels = req.nextUrl.searchParams.get('levels') ?? '';
  if (!/^\d{1,12}$/.test(id) || !/^[a-z_,]{1,80}$/.test(levels)) return problem(400, 'Bad Request', 'area_id and levels required');
  const res = await forward(`/v1/areas/${id}/boundaries?levels=${encodeURIComponent(levels)}`);
  if (!res.ok) return relay(res);
  return new NextResponse(await res.text(), {
    headers: { 'content-type': 'application/geo+json', 'cache-control': 'public, max-age=3600, s-maxage=3600' },
  });
}
