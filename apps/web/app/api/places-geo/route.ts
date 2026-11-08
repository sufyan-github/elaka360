import { NextResponse, type NextRequest } from 'next/server';

const API_URL = process.env.API_URL ?? 'http://localhost:4000';

/** Proxy for map pins (GeoJSON), cached briefly at the edge. */
export async function GET(req: NextRequest) {
  const params = new URLSearchParams();
  for (const k of ['area_id', 'category']) {
    const v = req.nextUrl.searchParams.get(k);
    if (v) params.set(k, v);
  }
  const res = await fetch(`${API_URL}/v1/places/geojson?${params}`, { next: { revalidate: 300 } });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { 'content-type': 'application/geo+json', 'cache-control': 'public, max-age=60, s-maxage=300' },
  });
}
