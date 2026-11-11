'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { LiveMap, type ScopeKey } from '@/components/map/LiveMap';

const CATS = ['', 'education', 'health', 'government', 'emergency', 'tourism', 'religious', 'transport', 'finance'] as const;
const SCOPE_KEYS: ScopeKey[] = ['district', 'division'];

/** Live map of Rajshahi District / Division: outlines, places loaded for the visible area, refreshed every minute. */
export function MapExplorer() {
  const t = useTranslations('LiveMap');
  const [scope, setScope] = useState<ScopeKey>('district');
  const [category, setCategory] = useState('');
  const [layers, setLayers] = useState({ coarse: true, fine: true, places: true });
  const chip = (on: boolean) => `whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${on ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`;
  return (
    <>
      <div className="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label={t('scope')}>
        {SCOPE_KEYS.map((key) => (
          <button type="button" key={key} aria-pressed={scope === key} onClick={() => setScope(key)} className={chip(scope === key)}>
            {t(`scopes.${key}`)}
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
