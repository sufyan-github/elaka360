'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { MapView } from '@/components/map/MapView';

const CATS = ['', 'education', 'health', 'government', 'tourism', 'religious', 'emergency', 'transport'] as const;

export function MapExplorer() {
  const t = useTranslations('MapExplorer');
  const [category, setCategory] = useState('');
  return (
    <>
      <div className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
        {CATS.map((key) => (
          <button type="button" key={key} aria-pressed={category === key} onClick={() => setCategory(key)} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${category === key ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
            {t(`cat.${key || 'all'}`)}
          </button>
        ))}
      </div>
      <MapView category={category || undefined} className="mt-3 h-[70dvh]" />
      <p className="mt-2 text-xs text-muted">{t('note')}</p>
    </>
  );
}
