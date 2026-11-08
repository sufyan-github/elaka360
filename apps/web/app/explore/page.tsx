import Link from 'next/link';
import type { Metadata } from 'next';
import { LEVEL_LABEL, formatNumber, nameOf, type AdminLevel } from '@elaka360/shared';
import { api } from '@/lib/api';
import { AreaCard } from '@/components/cards';
import { Section } from '@/components/ui';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'অন্বেষণ — বিভাগ, জেলা, উপজেলা' };

const TABS: AdminLevel[] = ['division', 'district', 'upazila', 'city_corporation'];

export default async function ExplorePage({ searchParams }: { searchParams: Promise<{ level?: string; division?: string }> }) {
  const sp = await searchParams;
  const level = (TABS.includes(sp.level as AdminLevel) ? sp.level : 'division') as AdminLevel;
  const divisions = await api.areas('division');
  const divisionId = sp.division ? Number(sp.division) : undefined;

  let items = (await api.areas(level, undefined, 500)).items;
  if (divisionId && level !== 'division') {
    const detail = await api.areaByPath(divisions.items.find((d) => d.id === divisionId)?.path ?? '');
    const districtIds = new Set(detail.children.map((c) => c.id));
    items = level === 'district' ? detail.children : items.filter((a) => a.parent_id !== null && districtIds.has(a.parent_id));
  }

  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">বাংলাদেশ ঘুরে দেখুন</h1>
        <p className="text-sm text-muted">বিভাগ থেকে ইউনিয়ন — প্রতিটি এলাকার তথ্য এক জায়গায়।</p>
      </div>
      <div className="scrollbar-none -mx-4 mt-4 flex gap-2 overflow-x-auto px-4" role="tablist">
        {TABS.map((t) => (
          <Link
            key={t}
            href={`/explore?level=${t}${divisionId ? `&division=${divisionId}` : ''}`}
            role="tab"
            aria-selected={t === level}
            className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium ${t === level ? 'bg-primary text-white' : 'border border-line bg-surface'}`}
          >
            {LEVEL_LABEL[t].bn}
          </Link>
        ))}
      </div>
      {level !== 'division' && (
        <div className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
          <Link href={`/explore?level=${level}`} className={`whitespace-nowrap rounded-full px-3 py-1 text-xs ${!divisionId ? 'bg-tint font-semibold text-primary' : 'border border-line'}`}>
            সকল বিভাগ
          </Link>
          {divisions.items.map((d) => (
            <Link key={d.id} href={`/explore?level=${level}&division=${d.id}`} className={`whitespace-nowrap rounded-full px-3 py-1 text-xs ${divisionId === d.id ? 'bg-tint font-semibold text-primary' : 'border border-line'}`}>
              {nameOf(d, 'bn')}
            </Link>
          ))}
        </div>
      )}
      <Section title={`${LEVEL_LABEL[level].plural_bn} (${formatNumber(items.length)})`}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {items.map((a) => (
            <AreaCard key={a.id} area={a} />
          ))}
        </div>
      </Section>
    </>
  );
}
