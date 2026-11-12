import { NextResponse, type NextRequest } from 'next/server';
import { adminFetch, qs } from '@/lib/api';

/**
 * Area options for the cascading pickers. Uses the admin list (all evidence levels, scoped to the
 * staff member's area) so unpublished areas can be chosen too. Read-only.
 */
export async function GET(req: NextRequest) {
  const p = req.nextUrl.searchParams;
  const level = p.get('level') ?? '';
  const parent = p.get('parent_id') ?? '';
  if (!/^[a-z_]{3,20}$/.test(level) || (parent && !/^\d{1,12}$/.test(parent))) {
    return NextResponse.json({ detail: 'bad query' }, { status: 400 });
  }
  const res = await adminFetch(`/v1/admin/areas${qs({ level, parent_id: parent, limit: 200 })}`);
  if (!res.ok) return NextResponse.json(await res.json().catch(() => ({ detail: `HTTP ${res.status}` })), { status: res.status });
  const data = (await res.json()) as { items: { id: number; name_bn: string; name_en: string; production_eligible: boolean; evidence_level: string }[] };
  return NextResponse.json({
    items: data.items.map(({ id, name_bn, name_en, production_eligible, evidence_level }) => ({ id, name_bn, name_en, production_eligible, evidence_level })),
  });
}
