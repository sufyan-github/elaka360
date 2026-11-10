import { redirect } from 'next/navigation';
import type { Metadata } from 'next';
import type { SavedItem } from '@elaka360/shared';
import { authedGet, currentUser } from '@/lib/session';
import { AreaCard, PlaceCard } from '@/components/cards';
import { EmptyState, Section } from '@/components/ui';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'সংরক্ষিত', robots: { index: false } };

export default async function SavedPage() {
  if (!(await currentUser())) redirect('/login?next=/saved');
  const saved = (await authedGet<{ items: SavedItem[] }>('/v1/me/saved'))?.items ?? [];
  const places = saved.filter((s) => s.place);
  const areas = saved.filter((s) => s.area);
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">সংরক্ষিত এলাকা ও স্থান</h1>
      {!saved.length && (
        <div className="mt-4">
          <EmptyState title="এখনো কিছু সংরক্ষণ করেননি" body="যেকোনো এলাকা বা স্থানের পাতায় “সংরক্ষণ” চাপুন।" />
        </div>
      )}
      {areas.length > 0 && (
        <Section title="এলাকা">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{areas.map((s) => <AreaCard key={s.id} area={s.area!} />)}</div>
        </Section>
      )}
      {places.length > 0 && (
        <Section title="স্থান">
          <div className="grid gap-3 md:grid-cols-2">{places.map((s) => <PlaceCard key={s.id} place={s.place!} />)}</div>
        </Section>
      )}
      <p className="mt-6 text-xs text-muted">অফলাইন ডাউনলোড (জেলাভিত্তিক প্যাক) এখনো চালু হয়নি; জরুরি পাতা ও হটলাইন অফলাইনেও খোলে।</p>
    </div>
  );
}
