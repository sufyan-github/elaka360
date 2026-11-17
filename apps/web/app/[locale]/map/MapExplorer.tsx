'use client';

import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { LiveMap, type MapScope } from '@/components/map/LiveMap';
import { localName } from '@/lib/locale';
import type { Locale } from '@elaka360/shared';

const CATS = ['', 'education', 'health', 'government', 'emergency', 'tourism', 'religious', 'transport', 'finance'] as const;
/** Shown until /data/map/scopes.json loads (and if it cannot): the first division collected. */
const FALLBACK: MapScope[] = [
  { id: 20015, kind: 'district', division_id: 10002, name_bn: 'রাজশাহী', name_en: 'Rajshahi' },
  { id: 10002, kind: 'division', division_id: 10002, name_bn: 'রাজশাহী', name_en: 'Rajshahi' },
];

/** Live map: each collected division's head district and the whole division; outlines, places and their counts. */
export function MapExplorer() {
  const t = useTranslations('LiveMap');
  const locale = useLocale() as Locale;
  const [scopes, setScopes] = useState<MapScope[]>(FALLBACK);
  const [scope, setScope] = useState<MapScope>(FALLBACK[0]!);
  const [category, setCategory] = useState('');
  const [layers, setLayers] = useState({ coarse: true, fine: true, places: true });

  useEffect(() => {
    fetch('/data/map/scopes.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((list: MapScope[] | null) => {
        if (!list?.length) return;
        setScopes(list);
        setScope((cur) => list.find((x) => x.id === cur.id) ?? list[0]!);
      })
      .catch(() => undefined);
  }, []);

  const chip = (on: boolean) => `whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${on ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`;
  return (
    <>
      <div className="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label={t('scope')}>
        {scopes.map((s) => (
          <button type="button" key={s.id} aria-pressed={scope.id === s.id} onClick={() => setScope(s)} className={chip(scope.id === s.id)}>
            {localName({ name_bn: s.name_bn, name_en: s.name_en }, locale)} {t(`kind.${s.kind}`)}
          </button>
        ))}
      </div>
      <div className="scrollbar-none -mx-4 mt-2 flex gap-2 overflow-x-auto px-4" role="group" aria-label={t('category')}>
        {CATS.map((key) => (
          <button type="button" key={key} aria-pressed={category === key} onClick={() => setCategory(key)} className={chip(category === key)}>
            {t(`cat.${key || 'all'}`)}
          </button>
        ))}
      </div>
      <fieldset className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        <legend className="sr-only">{t('layers')}</legend>
        {(['coarse', 'fine', 'places'] as const).map((k) => (
          <label key={k} className="flex items-center gap-1.5">
            <input type="checkbox" checked={layers[k]} onChange={(e) => setLayers((l) => ({ ...l, [k]: e.target.checked }))} className="h-4 w-4 accent-primary" />
            {t(`layer.${k}`)}
          </label>
        ))}
      </fieldset>
      <LiveMap scope={scope} category={category} layers={layers} />
      <p className="mt-2 text-xs text-muted">{t('note')}</p>
    </>
  );
}
