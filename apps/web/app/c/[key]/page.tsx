import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { formatNumber } from '@elaka360/shared';
import { api } from '@/lib/api';
import { PlaceCard } from '@/components/cards';
import { EmptyState, Section } from '@/components/ui';

/* Filters and paging come from the query string, so this page renders per request; its API reads are cached for 5 minutes. */

type Props = { params: Promise<{ key: string }>; searchParams: Promise<{ area?: string; sub?: string; cursor?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { key } = await params;
  const cat = (await api.categories()).find((c) => c.key === key);
  return { title: cat?.name_bn ?? 'ক্যাটাগরি' };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const { key } = await params;
  const sp = await searchParams;
  const cat = (await api.categories()).find((c) => c.key === key);
  if (!cat) notFound();
  const areaId = sp.area && /^\d{1,12}$/.test(sp.area) ? Number(sp.area) : undefined;
  const filter = sp.sub && cat.children?.some((s) => s.key === sp.sub) ? sp.sub : key;
  const cursor = sp.cursor && /^[A-Za-z0-9_-]{1,16}$/.test(sp.cursor) ? sp.cursor : undefined;
  const places = await api.places({ category: filter, areaId, limit: 30, cursor });
  const link = (o: { sub?: string; cursor?: string }) => {
    const p = new URLSearchParams();
    if (areaId) p.set('area', String(areaId));
    if (o.sub) p.set('sub', o.sub);
    if (o.cursor) p.set('cursor', o.cursor);
    const s = p.toString();
    return `/c/${key}${s ? `?${s}` : ''}`;
  };
  const subKey = filter === key ? undefined : filter;

  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">{cat.name_bn}</h1>
        <p className="font-en text-sm text-muted">{cat.name_en}</p>
      </div>
      <nav aria-label="উপ-ক্যাটাগরি" className="scrollbar-none -mx-4 mt-4 flex gap-2 overflow-x-auto px-4">
        <Link href={link({})} aria-current={filter === key ? 'page' : undefined} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${filter === key ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
          সব
        </Link>
        {cat.children?.map((s) => (
          <Link key={s.key} href={link({ sub: s.key })} aria-current={filter === s.key ? 'page' : undefined} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${filter === s.key ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
            {s.name_bn}
          </Link>
        ))}
      </nav>
      <Section title={`মোট পাওয়া গেছে: ${formatNumber(places.total)}টি`}>
        {places.items.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {places.items.map((p) => <PlaceCard key={p.public_id} place={p} />)}
          </div>
        ) : (
          <EmptyState title="এই ক্যাটাগরিতে এখনো কোনো প্রকাশিত তথ্য নেই" body="পাইলট পর্যায়ে শুধু রাজশাহীর কয়েকটি উৎসসহ স্থান প্রকাশিত হয়েছে।" />
        )}
        {(cursor || places.next_cursor) && (
          <div className="mt-4 flex justify-between text-sm">
            {cursor ? <Link href={link({ sub: subKey })} className="text-secondary underline">শুরুতে ফিরুন</Link> : <span />}
            {places.next_cursor && <Link href={link({ sub: subKey, cursor: places.next_cursor })} className="text-secondary underline">পরের পাতা</Link>}
          </div>
        )}
      </Section>
    </>
  );
}
