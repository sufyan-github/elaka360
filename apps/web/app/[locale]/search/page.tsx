import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { LEVEL_LABEL } from '@elaka360/shared';
import { ApiError, api, type SearchResult } from '@/lib/api';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { AreaCard, PlaceCard } from '@/components/cards';
import { SearchBox } from '@/components/SearchBox';
import { EmptyState, Section } from '@/components/ui';

type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ q?: string; type?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Search' });
  return { title: t('title'), alternates: localeAlternates(locale, '/search') };
}

const TYPES = [{ key: '', label: 'typeAll' }, { key: 'area', label: 'typeArea' }, { key: 'place', label: 'typePlace' }] as const;

export default async function SearchPage({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Search');
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
        <h1 className="sr-only">{t('title')}</h1>
        <SearchBox defaultValue={q} autoFocus={!q} />
        <p className="mt-2 text-xs text-muted">{t('hint')}</p>
      </div>
      {q.length >= 2 && (
        <nav aria-label={t('typeNav')} className="mt-3 flex gap-2">
          {TYPES.map((x) => (
            <Link key={x.key} href={`/search?q=${encodeURIComponent(q)}${x.key ? `&type=${x.key}` : ''}`} aria-current={type === x.key ? 'page' : undefined}
              className={`rounded-full px-3 py-1.5 text-sm ${type === x.key ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
              {t(x.label)}
            </Link>
          ))}
        </nav>
      )}
      {failed && <div className="mt-6"><EmptyState title={t('failedTitle')} body={t('failedBody')} /></div>}
      {result && (
        <>
          {result.areas.length > 0 && (
            <Section title={t('areas')}>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {result.areas.map((a) => <AreaCard key={a.id} area={a} sub={LEVEL_LABEL[a.level][locale]} />)}
              </div>
            </Section>
          )}
          {result.places.length > 0 && (
            <Section title={t('places')}>
              <div className="grid gap-3 md:grid-cols-2">
                {result.places.map((p) => <PlaceCard key={p.public_id} place={p} />)}
              </div>
            </Section>
          )}
          {!result.areas.length && !result.places.length && (
            <div className="mt-6">
              <EmptyState title={t('noResults', { q })} body={t('noResultsBody')} />
            </div>
          )}
        </>
      )}
    </>
  );
}
