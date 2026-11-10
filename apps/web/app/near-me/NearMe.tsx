'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { LocateFixed } from 'lucide-react';
import type { PlaceSummary } from '@elaka360/shared';
import { formatDistance } from '@elaka360/shared';
import { PlaceCard } from '@/components/cards';

const RADII = [500, 2000, 5000, 20000];
const CATS = [
  { key: '', label: 'সব' }, { key: 'health', label: 'স্বাস্থ্য' }, { key: 'education', label: 'শিক্ষা' },
  { key: 'emergency', label: 'জরুরি' }, { key: 'tourism', label: 'পর্যটন' }, { key: 'religious', label: 'ধর্মীয়' },
];
// Fallback: central Rajshahi (pilot area) when location is denied.
const FALLBACK = { lat: 24.3745, lon: 88.6042 };

export function NearMe({ initialCategory = '' }: { initialCategory?: string }) {
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
      .catch((e: Error) => { if (e.name !== 'AbortError') setError('তথ্য আনা যায়নি। আবার চেষ্টা করুন।'); });
    return () => ctrl.abort();
  }, [pos, radius, category]);

  return (
    <div>
      <div className="mt-4 flex items-center justify-between gap-2 rounded-card border border-line bg-surface p-3">
        <div className="text-sm">
          <div className="font-semibold">বর্তমান অবস্থান</div>
          <div className="text-muted">{pos ? (usingFallback ? 'রাজশাহী শহর (আপনার অবস্থান পাওয়া যায়নি)' : 'আপনার অবস্থান (শুধু আপনার ব্রাউজারে ব্যবহৃত হয়, সংরক্ষণ করা হয় না)') : 'অবস্থান খোঁজা হচ্ছে…'}</div>
        </div>
        <button type="button" onClick={locate} className="inline-flex items-center gap-1 rounded-chip border border-line px-3 py-2 text-sm font-medium text-secondary">
          <LocateFixed className="h-4 w-4" /> অবস্থান আপডেট
        </button>
      </div>
      <div className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
        {CATS.map((c) => (
          <button type="button" key={c.key} aria-pressed={category === c.key} onClick={() => setCategory(c.key)} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${category === c.key ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
            {c.label}
          </button>
        ))}
        {RADII.map((r) => (
          <button type="button" key={r} aria-pressed={radius === r} onClick={() => setRadius(r)} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${radius === r ? 'bg-tint font-semibold text-primary' : 'border border-line bg-surface'}`}>
            {formatDistance(r)}
          </button>
        ))}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2" aria-live="polite">
        {error && <p className="text-sm text-danger">{error}</p>}
        {!error && items === null && <p className="text-sm text-muted">লোড হচ্ছে…</p>}
        {items?.length === 0 && <p className="text-sm text-muted">এই দূরত্বের মধ্যে কোনো প্রকাশিত স্থান পাওয়া যায়নি। দূরত্ব বাড়িয়ে দেখুন। জরুরি প্রয়োজনে <Link href="/emergency" className="underline">৯৯৯</Link>।</p>}
        {items?.map((p) => <PlaceCard key={p.public_id} place={p} />)}
      </div>
    </div>
  );
}
