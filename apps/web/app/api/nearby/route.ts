import type { NextRequest } from 'next/server';
import { forward, relay } from '@/lib/http';

/** Proxy for the client-side Near me page. Coordinates are never logged or cached (private, no-store). */
export async function GET(req: NextRequest) {
  const params = new URLSearchParams();
  for (const k of ['lat', 'lon', 'radius_m', 'category', 'limit']) {
    const v = req.nextUrl.searchParams.get(k);
    if (v) params.set(k, v);
  }
  return relay(await forward(`/v1/places/nearby?${params}`));
}
