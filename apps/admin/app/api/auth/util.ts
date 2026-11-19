import { NextResponse, type NextRequest } from 'next/server';

export const forbidden = () =>
  NextResponse.json({ title: 'Forbidden', status: 403, detail: 'cross-origin request rejected' }, { status: 403 });

export async function readJson(req: NextRequest): Promise<Record<string, unknown>> {
  try {
    const b = await req.json();
    return b && typeof b === 'object' && !Array.isArray(b) ? (b as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

/** Pass an API problem response through (status + RFC 9457 body). */
export async function relay(res: Response) {
  let body: Record<string, unknown> = { title: res.statusText, status: res.status };
  try {
    body = (await res.json()) as Record<string, unknown>;
  } catch { /* keep default */ }
  return NextResponse.json(body, { status: res.status });
}
