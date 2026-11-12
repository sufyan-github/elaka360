'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { LocateFixed } from 'lucide-react';
import type { PlaceSummary } from '@elaka360/shared';
import { formatDistance } from '@elaka360/shared';
import { PlaceCard } from '@/components/cards';
import { Link } from '@/i18n/navigation';

const RADII = [500, 2000, 5000, 20000];
const CATS = ['', 'health', 'education', 'emergency', 'tourism', 'religious'] as const;
// Fallback: central Rajshahi (pilot area) when location is denied.
const FALLBACK = { lat: 24.3745, lon: 88.6042 };

export function NearMe({ initialCategory = '' }: { initialCategory?: string }) {
  const t = useTranslations('NearMe');
  const tCat = useTranslations('MapExplorer');
  const locale = useLocale();
  const [pos, setPos] = useState<{ lat: number; lon: number } | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);
  const [radius, setRadius] = useState(5000);
  const [category, setCategory] = useState(initialCategory);
  const [items, setItems] = useState<PlaceSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const locate = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setPos(FALLBACK);
      setUsingFallback(true);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => { setPos({ lat: p.coords.latitude, lon: p.coords.longitude }); setUsingFallback(false); },
      () => { setPos(FALLBACK); setUsingFallback(true); },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 },
    );
  }, []);

  useEffect(locate, [locate]);

  useEffect(() => {
    if (!pos) return;
    const inBd = pos.lat >= 20 && pos.lat <= 27 && pos.lon >= 88 && pos.lon <= 93;
    const q = inBd ? pos : FALLBACK;
    if (!inBd) setUsingFallback(true);
    const params = new URLSearchParams({ lat: String(q.lat), lon: String(q.lon), radius_m: String(radius) });
    if (category) params.set('category', category);
    setItems(null);
    setError(null);
    // Abort the previous request so a slow answer for an old filter never overwrites a newer one (finding C18).
    const ctrl = new AbortController();
    fetch(`/api/nearby?${params}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { items: PlaceSummary[] }) => setItems(d.items))
      .catch((e: Error) => { if (e.name !== 'AbortError') setError(t('loadFailed')); });
    return () => ctrl.abort();
  }, [pos, radius, category]);

  return (
    <div>
      <div className="mt-4 flex items-center justify-between gap-2 rounded-card border border-line bg-surface p-3">
        <div className="text-sm">
          <div className="font-semibold">{t('current')}</div>
          <div className="text-muted">{pos ? (usingFallback ? t('fallback') : t('yours')) : t('locating')}</div>
        </div>
        <button type="button" onClick={locate} className="inline-flex items-center gap-1 rounded-chip border border-line px-3 py-2 text-sm font-medium text-secondary">
          <LocateFixed className="h-4 w-4" /> {t('update')}
        </button>
      </div>
      <div className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
        {CATS.map((key) => (
          <button type="button" key={key} aria-pressed={category === key} onClick={() => setCategory(key)} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${category === key ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
            {tCat(`cat.${key || 'all'}`)}
          </button>
        ))}
        {RADII.map((r) => (
          <button type="button" key={r} aria-pressed={radius === r} onClick={() => setRadius(r)} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${radius === r ? 'bg-tint font-semibold text-primary' : 'border border-line bg-surface'}`}>
            {formatDistance(r, locale)}
          </button>
        ))}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2" aria-live="polite">
        {error && <p className="text-sm text-danger">{error}</p>}
        {!error && items === null && <p className="text-sm text-muted">{t('loading')}</p>}
        {items?.length === 0 && <p className="text-sm text-muted">{t.rich('empty', { link: (c) => <Link href="/emergency" className="underline">{c}</Link> })}</p>}
        {items?.map((p) => <PlaceCard key={p.public_id} place={p} />)}
      </div>
    </div>
  );
}
