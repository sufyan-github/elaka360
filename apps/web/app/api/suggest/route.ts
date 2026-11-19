import { NextResponse, type NextRequest } from 'next/server';
import { forward } from '@/lib/http';

export async function GET(req: NextRequest) {
  const q = (req.nextUrl.searchParams.get('q') ?? '').slice(0, 60);
  if (!q.trim()) return NextResponse.json({ items: [] });
  const res = await forward(`/v1/search/suggest?q=${encodeURIComponent(q)}`);
  if (!res.ok) return NextResponse.json({ items: [] }, { headers: { 'cache-control': 'no-store' } });
  return new NextResponse(await res.text(), { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=60' } });
}
