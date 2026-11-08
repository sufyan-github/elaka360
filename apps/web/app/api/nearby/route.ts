import { NextResponse, type NextRequest } from 'next/server';

const API_URL = process.env.API_URL ?? 'http://localhost:4000';

/** Proxy for the client-side Near me page, so the API URL stays server-side. */
export async function GET(req: NextRequest) {
  const allowed = ['lat', 'lon', 'radius_m', 'category', 'limit'];
  const params = new URLSearchParams();
  for (const k of allowed) {
    const v = req.nextUrl.searchParams.get(k);
    if (v) params.set(k, v);
  }
  const res = await fetch(`${API_URL}/v1/places/nearby?${params}`, { cache: 'no-store' });
  return new NextResponse(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } });
}
