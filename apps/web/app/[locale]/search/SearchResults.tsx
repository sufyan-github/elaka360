'use client';

import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { LEVEL_LABEL, type Locale } from '@elaka360/shared';
import { AreaCard, PlaceCard } from '@/components/cards';
import { EmptyState, Section } from '@/components/ui';
import { search, type BrowserSearchResult } from '@/lib/browser-search';

/** Results of /search, computed in the browser from the static index (lib/browser-search.ts). */
export function SearchResults({ q, type }: { q: string; type: '' | 'area' | 'place' }) {
  const t = useTranslations('Search');
  const locale = useLocale() as Locale;
  const [state, setState] = useState<{ q: string; result: BrowserSearchResult | null; failed: boolean }>({ q: '', result: null, failed: false });

  useEffect(() => {
    let cancelled = false;
    setState({ q, result: null, failed: false });
    search(q, { type: type || undefined })
      .then((result) => { if (!cancelled) setState({ q, result, failed: false }); })
      .catch(() => { if (!cancelled) setState({ q, result: null, failed: true }); });
    return () => { cancelled = true; };
  }, [q, type]);

  if (state.failed) return <div className="mt-6"><EmptyState title={t('failedTitle')} body={t('failedBody')} /></div>;
  const result = state.result;
  if (!result) return <p className="mt-6 text-sm text-muted" role="status">{t('loading')}</p>;
  return (
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
            {result.places.map((p) => <PlaceCard key={p.slug} place={p} />)}
          </div>
        </Section>
      )}
      {!result.areas.length && !result.places.length && (
        <div className="mt-6"><EmptyState title={t('noResults', { q })} body={t('noResultsBody')} /></div>
      )}
    </>
  );
}
