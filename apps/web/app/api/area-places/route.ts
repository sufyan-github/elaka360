import { NextResponse, type NextRequest } from 'next/server';
import { forward, relay } from '@/lib/http';

/** Places filed under one area (with or without coordinates), for the live map's side panel. */
export async function GET(req: NextRequest) {
  const params = new URLSearchParams();
  for (const k of ['area_id', 'category', 'limit']) {
    const v = req.nextUrl.searchParams.get(k);
    if (v) params.set(k, v);
  }
  const res = await forward(`/v1/places?${params}`);
  if (!res.ok) return relay(res);
  return new NextResponse(await res.text(), {
    headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=60, s-maxage=60' },
  });
}
