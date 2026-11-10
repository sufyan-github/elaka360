'use client';

import { useEffect, useState } from 'react';
import type { AdminLevel } from '@elaka360/shared';
import { LEVEL_LABEL } from '@elaka360/shared';
import type { AreaOption } from '@/lib/types';

type Opt = AreaOption & { level: AdminLevel };

async function load(levels: AdminLevel[], parentId?: string): Promise<Opt[]> {
  const lists = await Promise.all(levels.map(async (level) => {
    const q = new URLSearchParams({ level });
    if (parentId) q.set('parent_id', parentId);
    const res = await fetch(`/api/lookup/areas?${q}`, { headers: { accept: 'application/json' } });
    if (!res.ok) {
      const d = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new Error(d.detail ?? `HTTP ${res.status}`);
    }
    const d = (await res.json()) as { items: AreaOption[] };
    return d.items.map((i) => ({ ...i, level }));
  }));
  return lists.flat();
}

const STEPS: { label: string; en: string; levels: AdminLevel[] }[] = [
  { label: 'বিভাগ', en: 'Division', levels: ['division'] },
  { label: 'জেলা', en: 'District', levels: ['district'] },
  { label: 'উপজেলা / সিটি কর্পোরেশন', en: 'Upazila / City corp.', levels: ['upazila', 'city_corporation'] },
  { label: 'ইউনিয়ন / পৌরসভা', en: 'Union / Pourashava', levels: ['union', 'pourashava'] },
];

/**
 * Cascading division → district → upazila → union selects (admin area list, so unpublished areas are
 * included), plus a raw area_id field that overrides the selects. Submits `area_id`.
 */
export function AreaPicker({ idPrefix = 'ap', required, currentLabel, defaultRaw = '' }: { idPrefix?: string; required?: boolean; currentLabel?: string; defaultRaw?: string }) {
  const [sel, setSel] = useState<string[]>(['', '', '', '']);
  const [opts, setOpts] = useState<Opt[][]>([[], [], [], []]);
  const [loading, setLoading] = useState<number | null>(0);
  const [error, setError] = useState<string | null>(null);
  const [raw, setRaw] = useState(defaultRaw);

  useEffect(() => {
    let live = true;
    load(STEPS[0]!.levels).then((o) => { if (live) { setOpts((p) => [o, p[1]!, p[2]!, p[3]!]); setLoading(null); } })
      .catch((e: Error) => { if (live) { setError(e.message); setLoading(null); } });
    return () => { live = false; };
  }, []);

  function choose(step: number, value: string) {
    const nextSel = sel.map((v, i) => (i < step ? v : i === step ? value : ''));
    setSel(nextSel);
    setOpts((p) => p.map((o, i) => (i <= step ? o : [])));
    if (!value || step + 1 >= STEPS.length) return;
    const chosen = opts[step]!.find((o) => String(o.id) === value);
    // A city corporation has wards, not unions; stop the cascade there.
    if (chosen?.level === 'city_corporation') return;
    setLoading(step + 1);
    setError(null);
    load(STEPS[step + 1]!.levels, value)
      .then((o) => setOpts((p) => p.map((x, i) => (i === step + 1 ? o : x))))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(null));
  }

  const picked = [...sel].reverse().find(Boolean) ?? '';
  const value = raw.trim() || picked;

  return (
    <fieldset className="rounded-chip border border-line p-3">
      <legend className="px-1 text-sm font-medium">এলাকা <span className="font-en text-xs font-normal text-muted">· Area{required ? ' (required)' : ''}</span></legend>
      {currentLabel && <p className="mb-2 text-xs text-muted">বর্তমান: <span className="font-en">{currentLabel}</span> — বদলাতে চাইলে নিচে বেছে নিন, নইলে খালি রাখুন।</p>}
      <div className="grid gap-3 md:grid-cols-2">
        {STEPS.map((s, i) => (
          <div key={s.en}>
            <label htmlFor={`${idPrefix}-${i}`} className="mb-1 block text-xs font-medium text-muted">{s.label} <span className="font-en">· {s.en}</span></label>
            <select id={`${idPrefix}-${i}`} className="input" value={sel[i]} disabled={i > 0 && !opts[i]!.length} onChange={(e) => choose(i, e.target.value)}>
              <option value="">{loading === i ? 'লোড হচ্ছে…' : '— বেছে নিন —'}</option>
              {opts[i]!.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name_bn} ({o.name_en}){s.levels.length > 1 ? ` · ${LEVEL_LABEL[o.level].bn}` : ''}{o.production_eligible ? '' : ' · অপ্রকাশিত'}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
      <div className="mt-3">
        <label htmlFor={`${idPrefix}-raw`} className="mb-1 block text-xs font-medium text-muted">অথবা সরাসরি এলাকার আইডি <span className="font-en">· raw area_id</span></label>
        <input id={`${idPrefix}-raw`} inputMode="numeric" pattern="[0-9]*" className="input font-en" value={raw} onChange={(e) => setRaw(e.target.value)} placeholder="যেমন 30123" />
      </div>
      <input type="hidden" name="area_id" value={value} />
      <p className="mt-2 text-xs text-muted" aria-live="polite">নির্বাচিত area_id: <span className="font-en font-semibold">{value || '—'}</span></p>
      {error && <p role="alert" className="mt-2 text-xs text-danger">{error}</p>}
    </fieldset>
  );
}
