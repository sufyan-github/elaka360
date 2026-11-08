import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { formatNumber } from '@elaka360/shared';
import { api } from '@/lib/api';
import { PlaceCard } from '@/components/cards';
import { EmptyState, Section } from '@/components/ui';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ key: string }>; searchParams: Promise<{ area?: string; sub?: string }> };

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
  const areaId = sp.area && /^\d+$/.test(sp.area) ? Number(sp.area) : undefined;
  const filter = sp.sub && cat.children?.some((s) => s.key === sp.sub) ? sp.sub : key;
  const places = await api.places({ category: filter, areaId, limit: 50 });
  const base = `/c/${key}${areaId ? `?area=${areaId}` : ''}`;
  const sep = areaId ? '&' : '?';

  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">{cat.name_bn}</h1>
        <p className="font-en text-sm text-muted">{cat.name_en}</p>
      </div>
      <div className="scrollbar-none -mx-4 mt-4 flex gap-2 overflow-x-auto px-4">
        <Link href={base} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${filter === key ? 'bg-primary text-white' : 'border border-line bg-surface'}`}>
          সব
        </Link>
        {cat.children?.map((s) => (
          <Link key={s.key} href={`${base}${sep}sub=${s.key}`} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${filter === s.key ? 'bg-primary text-white' : 'border border-line bg-surface'}`}>
            {s.name_bn}
          </Link>
        ))}
      </div>
      <Section title={`মোট পাওয়া গেছে: ${formatNumber(places.items.length)}টি`}>
        {places.items.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {places.items.map((p) => (
              <PlaceCard key={p.public_id} place={p} />
            ))}
          </div>
        ) : (
          <EmptyState title="এই ক্যাটাগরিতে এখনো কোনো তথ্য নেই" body="পাইলট পর্যায়ে শুধু রাজশাহী জেলার কিছু যাচাইকৃত স্থান যুক্ত আছে।" />
        )}
      </Section>
    </>
  );
}
