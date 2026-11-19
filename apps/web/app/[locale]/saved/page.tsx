import { redirect } from 'next/navigation';
import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { SavedItem } from '@elaka360/shared';
import { authedGet, currentUser } from '@/lib/session';
import { asLocale } from '@/lib/locale';
import { localePath } from '@/lib/links';
import { localeAlternates } from '@/lib/meta';
import { AreaCard, PlaceCard } from '@/components/cards';
import { EmptyState, Section } from '@/components/ui';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Saved' });
  return { title: t('title'), robots: { index: false }, alternates: localeAlternates(locale, '/saved') };
}

export default async function SavedPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Saved');
  if (!(await currentUser())) redirect(`${localePath(locale, '/login')}?next=${localePath(locale, '/saved')}`);
  const saved = (await authedGet<{ items: SavedItem[] }>('/v1/me/saved'))?.items ?? [];
  const places = saved.filter((s) => s.place);
  const areas = saved.filter((s) => s.area);
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('heading')}</h1>
      {!saved.length && (
        <div className="mt-4">
          <EmptyState title={t('emptyTitle')} body={t('emptyBody')} />
        </div>
      )}
      {areas.length > 0 && (
        <Section title={t('areas')}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{areas.map((s) => <AreaCard key={s.id} area={s.area!} />)}</div>
        </Section>
      )}
      {places.length > 0 && (
        <Section title={t('places')}>
          <div className="grid gap-3 md:grid-cols-2">{places.map((s) => <PlaceCard key={s.id} place={s.place!} />)}</div>
        </Section>
      )}
      <p className="mt-6 text-xs text-muted">{t('offlineNote')}</p>
    </div>
  );
}
