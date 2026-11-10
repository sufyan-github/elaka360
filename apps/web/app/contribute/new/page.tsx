import type { Metadata } from 'next';
import { api } from '@/lib/api';
import { Wizard } from './Wizard';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'নতুন অবদান', robots: { index: false } };

const TYPES = ['new_place', 'correction', 'report'] as const;

export default async function NewContribution({ searchParams }: { searchParams: Promise<{ type?: string; place?: string; area?: string }> }) {
  const sp = await searchParams;
  const categories = await api.categories();
  const type = TYPES.includes(sp.type as never) ? (sp.type as (typeof TYPES)[number]) : 'new_place';
  const place = sp.place && /^[a-z0-9-]{1,120}$/.test(sp.place) ? sp.place : undefined;
  const area = sp.area && /^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(sp.area) ? sp.area : undefined;
  return (
    <div className="mx-auto max-w-xl pt-6">
      <h1 className="text-2xl font-bold">নতুন অবদান</h1>
      <Wizard categories={categories.map((c) => ({ key: c.key, name: c.name_bn, subs: (c.children ?? []).map((s) => ({ key: s.key, name: s.name_bn })) }))}
        initialType={type} targetPlace={place} targetArea={area} />
    </div>
  );
}
