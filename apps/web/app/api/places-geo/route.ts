import { NextResponse, type NextRequest } from 'next/server';
import { forward, relay } from '@/lib/http';

/** Map pins (GeoJSON). Only successful responses are cacheable (finding C4). */
export async function GET(req: NextRequest) {
  const params = new URLSearchParams();
  for (const k of ['area_id', 'category', 'bbox']) {
    const v = req.nextUrl.searchParams.get(k);
    if (v) params.set(k, v);
  }
  const res = await forward(`/v1/places/geojson?${params}`);
  if (!res.ok) return relay(res);
  return new NextResponse(await res.text(), {
    headers: { 'content-type': 'application/geo+json', 'cache-control': 'public, max-age=60, s-maxage=300' },
  });
}
