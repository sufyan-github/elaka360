import type { Metadata } from 'next';
import { LEVEL_LABEL } from '@elaka360/shared';
import { ApiError, api } from '@/lib/api';
import { AreaCard, PlaceCard } from '@/components/cards';
import { SearchBox } from '@/components/SearchBox';
import { EmptyState, Section } from '@/components/ui';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'খুঁজুন' };

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const q = ((await searchParams).q ?? '').trim();
  let result: Awaited<ReturnType<typeof api.search>> | null = null;
  if (q.length >= 2) {
    try {
      result = await api.search(q);
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 400)) throw e;
    }
  }
  return (
    <>
      <div className="pt-6">
        <SearchBox defaultValue={q} autoFocus={!q} />
        <p className="mt-2 text-xs text-muted">বাংলা বা ইংরেজিতে লিখুন — যেমন “রাজশাহী”, “paba”, “হাসপাতাল”।</p>
      </div>
      {result && (
        <>
          {result.areas.length > 0 && (
            <Section title="এলাকা">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {result.areas.map((a) => (
                  <AreaCard key={a.id} area={a} sub={LEVEL_LABEL[a.level].bn} />
                ))}
              </div>
            </Section>
          )}
          {result.places.length > 0 && (
            <Section title="প্রতিষ্ঠান ও স্থান">
              <div className="grid gap-3 md:grid-cols-2">
                {result.places.map((p) => (
                  <PlaceCard key={p.public_id} place={p} />
                ))}
              </div>
            </Section>
          )}
          {!result.areas.length && !result.places.length && (
            <div className="mt-6">
              <EmptyState title={`“${q}” এর জন্য কিছু পাওয়া যায়নি`} body="বানান পরীক্ষা করুন বা অন্য শব্দ দিয়ে চেষ্টা করুন।" />
            </div>
          )}
        </>
      )}
    </>
  );
}
