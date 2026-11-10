import Link from 'next/link';
import type { Metadata } from 'next';
import { LEVEL_LABEL } from '@elaka360/shared';
import { ApiError, api, type SearchResult } from '@/lib/api';
import { AreaCard, PlaceCard } from '@/components/cards';
import { SearchBox } from '@/components/SearchBox';
import { EmptyState, Section } from '@/components/ui';

export const metadata: Metadata = { title: 'খুঁজুন' };

const TYPES = [{ key: '', label: 'সব' }, { key: 'area', label: 'এলাকা' }, { key: 'place', label: 'স্থান' }];

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string; type?: string }> }) {
  const sp = await searchParams;
  const q = (sp.q ?? '').trim().slice(0, 80);
  const type = sp.type === 'area' || sp.type === 'place' ? sp.type : '';
  let result: SearchResult | null = null;
  let failed = false;
  if (q.length >= 2) {
    try {
      result = await api.search(q, { type: type || undefined });
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 400)) failed = true;
    }
  }
  return (
    <>
      <div className="pt-6">
        <h1 className="sr-only">খুঁজুন</h1>
        <SearchBox defaultValue={q} autoFocus={!q} />
        <p className="mt-2 text-xs text-muted">বাংলা বা ইংরেজিতে লিখুন — যেমন “রাজশাহী”, “rajsahi”, “paba”, “হাসপাতাল”।</p>
      </div>
      {q.length >= 2 && (
        <nav aria-label="ফলাফলের ধরন" className="mt-3 flex gap-2">
          {TYPES.map((t) => (
            <Link key={t.key} href={`/search?q=${encodeURIComponent(q)}${t.key ? `&type=${t.key}` : ''}`} aria-current={type === t.key ? 'page' : undefined}
              className={`rounded-full px-3 py-1.5 text-sm ${type === t.key ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
              {t.label}
            </Link>
          ))}
        </nav>
      )}
      {failed && <div className="mt-6"><EmptyState title="এই মুহূর্তে খোঁজা যাচ্ছে না" body="সার্ভারের সঙ্গে সংযোগ হয়নি। একটু পরে আবার চেষ্টা করুন।" /></div>}
      {result && (
        <>
          {result.areas.length > 0 && (
            <Section title="এলাকা">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {result.areas.map((a) => <AreaCard key={a.id} area={a} sub={LEVEL_LABEL[a.level].bn} />)}
              </div>
            </Section>
          )}
          {result.places.length > 0 && (
            <Section title="প্রতিষ্ঠান ও স্থান">
              <div className="grid gap-3 md:grid-cols-2">
                {result.places.map((p) => <PlaceCard key={p.public_id} place={p} />)}
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
