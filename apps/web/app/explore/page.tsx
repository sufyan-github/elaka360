import Link from 'next/link';
import type { Metadata } from 'next';
import { LEVEL_LABEL, formatNumber, nameOf, type AdminLevel, type AreaTreeNode } from '@elaka360/shared';
import { api } from '@/lib/api';
import { AreaCard } from '@/components/cards';
import { EmptyState, Section } from '@/components/ui';

export const metadata: Metadata = { title: 'অন্বেষণ — বিভাগ, জেলা, উপজেলা' };

const TABS: AdminLevel[] = ['division', 'district', 'upazila', 'city_corporation'];

export default async function ExplorePage({ searchParams }: { searchParams: Promise<{ level?: string; division?: string }> }) {
  const sp = await searchParams;
  const level = (TABS.includes(sp.level as AdminLevel) ? sp.level : 'division') as AdminLevel;
  const tree = await api.tree(1, 3);
  const divisions = tree.children ?? [];
  // An unknown ?division= is ignored instead of silently filtering against the wrong ids (finding C19).
  const division = divisions.find((d) => String(d.id) === sp.division);

  const scope: AreaTreeNode[] = division ? [division] : divisions;
  const districts = scope.flatMap((d) => d.children ?? []);
  const items: AreaTreeNode[] =
    level === 'division' ? divisions
    : level === 'district' ? districts.filter((d) => d.level === 'district')
    : districts.flatMap((d) => d.children ?? []).filter((c) => c.level === level);
  items.sort((a, b) => a.name_en.localeCompare(b.name_en));
  const pending = level === 'upazila' ? (await api.areaStats(division?.id ?? 1)).pending_counts.upazila ?? 0 : 0;

  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">বাংলাদেশ ঘুরে দেখুন</h1>
        <p className="text-sm text-muted">বিভাগ থেকে জেলা, উপজেলা ও সিটি কর্পোরেশন — উৎসসহ প্রকাশিত এলাকা।</p>
      </div>
      <nav aria-label="প্রশাসনিক স্তর" className="scrollbar-none -mx-4 mt-4 flex gap-2 overflow-x-auto px-4">
        {TABS.map((t) => (
          <Link key={t} href={`/explore?level=${t}${division ? `&division=${division.id}` : ''}`} aria-current={t === level ? 'page' : undefined}
            className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium ${t === level ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
            {LEVEL_LABEL[t].bn}
          </Link>
        ))}
      </nav>
      {level !== 'division' && (
        <nav aria-label="বিভাগ" className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
          <Link href={`/explore?level=${level}`} aria-current={!division ? 'page' : undefined} className={`whitespace-nowrap rounded-full px-3 py-1 text-xs ${!division ? 'bg-tint font-semibold text-primary' : 'border border-line'}`}>
            সকল বিভাগ
          </Link>
          {divisions.map((d) => (
            <Link key={d.id} href={`/explore?level=${level}&division=${d.id}`} aria-current={division?.id === d.id ? 'page' : undefined}
              className={`whitespace-nowrap rounded-full px-3 py-1 text-xs ${division?.id === d.id ? 'bg-tint font-semibold text-primary' : 'border border-line'}`}>
              {nameOf(d, 'bn')}
            </Link>
          ))}
        </nav>
      )}
      <Section title={`${LEVEL_LABEL[level].plural_bn} (${formatNumber(items.length)})`}>
        {items.length ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {items.map((a) => <AreaCard key={a.id} area={a} />)}
          </div>
        ) : (
          <EmptyState title="এই বিভাগে প্রকাশিত কোনো এলাকা নেই" />
        )}
        {pending > 0 && (
          <p className="mt-3 text-xs text-muted">
            আরও {formatNumber(pending)}টি উপজেলার তথ্য যাচাইয়ের অপেক্ষায় আছে। <Link href="/data-policy" className="underline">বিস্তারিত</Link>
          </p>
        )}
      </Section>
    </>
  );
}
