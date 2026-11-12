import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { nameOf } from '@elaka360/shared';
import { api } from '@/lib/api';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Wizard } from './Wizard';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ type?: string; place?: string; area?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Wizard' });
  return { title: t('title'), robots: { index: false }, alternates: localeAlternates(locale, '/contribute/new') };
}

const TYPES = ['new_place', 'correction', 'report'] as const;

export default async function NewContribution({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Wizard');
  const sp = await searchParams;
  const categories = await api.categories();
  const type = TYPES.includes(sp.type as never) ? (sp.type as (typeof TYPES)[number]) : 'new_place';
  const place = sp.place && /^[a-z0-9-]{1,120}$/.test(sp.place) ? sp.place : undefined;
  const area = sp.area && /^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(sp.area) ? sp.area : undefined;
  return (
    <div className="mx-auto max-w-xl pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <Wizard categories={categories.map((c) => ({ key: c.key, name: nameOf(c, locale), subs: (c.children ?? []).map((s) => ({ key: s.key, name: nameOf(s, locale) })) }))}
        initialType={type} targetPlace={place} targetArea={area} />
    </div>
  );
}
