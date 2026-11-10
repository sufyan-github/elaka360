'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LocateFixed } from 'lucide-react';
import { toBnDigits } from '@elaka360/shared';

type Cat = { key: string; name: string; subs: { key: string; name: string }[] };
type Type = 'new_place' | 'correction' | 'report';
interface Draft {
  type: Type; name_bn: string; name_en: string; category_key: string; address: string; description: string; phone: string; website: string;
  field: string; current_value: string; proposed_value: string; note: string;
  lat: number | null; lon: number | null; evidence: string; confirmed: boolean;
}

const STEPS = ['ধরন', 'তথ্য', 'অবস্থান', 'উৎস ও জমা'];
const DRAFT_KEY = 'e360-contribution-draft';
const EMPTY: Draft = { type: 'new_place', name_bn: '', name_en: '', category_key: '', address: '', description: '', phone: '', website: '',
  field: '', current_value: '', proposed_value: '', note: '', lat: null, lon: null, evidence: '', confirmed: false };

function problemText(status: number, detail?: string) {
  if (status === 401) return 'সেশন শেষ হয়েছে — আবার সাইন ইন করুন। আপনার খসড়া এই ডিভাইসে সংরক্ষিত আছে।';
  if (status === 429) return 'আজকের সীমা পূর্ণ হয়েছে। খসড়া সংরক্ষিত আছে; পরে জমা দিন।';
  return detail ? `জমা দেওয়া যায়নি: ${detail}` : 'জমা দেওয়া যায়নি। খসড়া এই ডিভাইসে সংরক্ষিত আছে।';
}

/** Four-step wizard. The draft is kept in this browser (works offline) until it is submitted. */
export function Wizard({ categories, initialType, targetPlace, targetArea }: { categories: Cat[]; initialType: Type; targetPlace?: string; targetArea?: string }) {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [d, setD] = useState<Draft>({ ...EMPTY, type: initialType });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setD((x) => ({ ...x, [k]: v }));

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(DRAFT_KEY) ?? 'null') as Draft | null;
      if (saved && saved.type === initialType && !targetPlace && !targetArea) setD({ ...EMPTY, ...saved });
    } catch { /* ignore */ }
  }, [initialType, targetPlace, targetArea]);
  useEffect(() => {
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(d)); } catch { /* storage blocked */ }
  }, [d]);

  const needsTarget = d.type !== 'new_place';
  const valid = [
    true,
    d.type === 'new_place' ? d.name_bn.trim().length >= 2 && !!d.category_key : d.type === 'correction' ? d.proposed_value.trim().length > 0 : d.note.trim().length >= 5,
    true,
    d.confirmed,
  ];

  function locate() {
    navigator.geolocation?.getCurrentPosition(
      (p) => { set('lat', Math.round(p.coords.latitude * 1e6) / 1e6); set('lon', Math.round(p.coords.longitude * 1e6) / 1e6); },
      () => setError('অবস্থান পাওয়া যায়নি। অবস্থান ছাড়াও জমা দিতে পারেন।'),
      { timeout: 10000 },
    );
  }

  async function submit(asDraft: boolean) {
    setBusy(true); setError(null);
    const payload = d.type === 'new_place'
      ? { name_bn: d.name_bn, name_en: d.name_en || undefined, category_key: d.category_key, address: d.address || undefined,
          description: d.description || undefined, website: d.website || undefined, phones: d.phone ? [d.phone] : undefined }
      : { field: d.field || undefined, current_value: d.current_value || undefined, proposed_value: d.proposed_value || undefined, note: d.note || undefined };
    const evidence = d.evidence.split(/\s+/).filter((u) => /^https?:\/\//.test(u)).slice(0, 5).map((url) => ({ url }));
    const res = await fetch('/api/u/contributions', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: d.type, payload, evidence, lat: d.lat, lon: d.lon, confirmed_accurate: d.confirmed, submit: !asDraft,
        ...(targetPlace ? { target_place_slug: targetPlace } : targetArea ? { target_area_path: targetArea } : {}),
      }),
    });
    setBusy(false);
    if (!res.ok) {
      const p = await res.json().catch(() => ({}));
      return setError(problemText(res.status, p.detail));
    }
    try { localStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ }
    router.push('/me');
    router.refresh();
  }

  const input = 'mt-1 w-full rounded-chip border border-line bg-surface px-3 py-2';
  const label = 'block text-sm font-medium';
  return (
    <div className="mt-4">
      <ol className="flex gap-1 text-xs" aria-label="ধাপ">
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === step ? 'step' : undefined} className={`flex-1 rounded-full px-2 py-1 text-center ${i === step ? 'bg-primary text-on-primary' : i < step ? 'bg-tint text-primary' : 'border border-line'}`}>
            {toBnDigits(i + 1)}. {s}
          </li>
        ))}
      </ol>

      <div className="mt-4 space-y-4 rounded-card border border-line bg-surface p-4">
        {step === 0 && (
          <fieldset className="space-y-2">
            <legend className="font-semibold">কী ধরনের অবদান?</legend>
            {([['new_place', 'নতুন স্থান'], ['correction', 'ভুল তথ্য সংশোধন'], ['report', 'সমস্যা জানান']] as [Type, string][]).map(([t, l]) => (
              <label key={t} className="flex items-center gap-2 rounded-chip border border-line p-3">
                <input type="radio" name="type" checked={d.type === t} onChange={() => set('type', t)} /> {l}
              </label>
            ))}
            {needsTarget && (
              <p className="text-sm text-muted">{targetPlace ? `স্থান: ${targetPlace}` : targetArea ? `এলাকা: ${targetArea}` : 'সংশোধনের জন্য সংশ্লিষ্ট পাতার “ভুল তথ্য জানান” লিংক থেকে আসুন।'}</p>
            )}
          </fieldset>
        )}

        {step === 1 && d.type === 'new_place' && (
          <>
            <label className={label}>নাম (বাংলা) *<input value={d.name_bn} onChange={(e) => set('name_bn', e.target.value)} maxLength={120} className={input} /></label>
            <label className={label}>নাম (ইংরেজি)<input value={d.name_en} onChange={(e) => set('name_en', e.target.value)} maxLength={120} className={input} /></label>
            <label className={label}>ধরন *
              <select value={d.category_key} onChange={(e) => set('category_key', e.target.value)} className={input}>
                <option value="">বেছে নিন</option>
                {categories.map((c) => (
                  <optgroup key={c.key} label={c.name}>
                    {c.subs.map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}
                  </optgroup>
                ))}
              </select>
            </label>
            <label className={label}>ঠিকানা<input value={d.address} onChange={(e) => set('address', e.target.value)} maxLength={200} className={input} /></label>
            <label className={label}>বিবরণ<textarea value={d.description} onChange={(e) => set('description', e.target.value)} maxLength={500} rows={3} className={input} />
              <span className="text-xs text-muted">{toBnDigits(d.description.length)}/৫০০</span></label>
            <label className={label}>প্রতিষ্ঠানের ফোন (ব্যক্তিগত নম্বর নয়)<input value={d.phone} onChange={(e) => set('phone', e.target.value)} inputMode="tel" maxLength={20} className={input} /></label>
            <label className={label}>ওয়েবসাইট<input value={d.website} onChange={(e) => set('website', e.target.value)} type="url" maxLength={300} className={input} /></label>
          </>
        )}
        {step === 1 && d.type !== 'new_place' && (
          <>
            <label className={label}>কোন তথ্য?<input value={d.field} onChange={(e) => set('field', e.target.value)} placeholder="যেমন: ফোন নম্বর, ঠিকানা, নাম" maxLength={60} className={input} /></label>
            {d.type === 'correction' && (
              <>
                <label className={label}>বর্তমানে যা দেখানো হচ্ছে<input value={d.current_value} onChange={(e) => set('current_value', e.target.value)} maxLength={500} className={input} /></label>
                <label className={label}>সঠিক তথ্য *<input value={d.proposed_value} onChange={(e) => set('proposed_value', e.target.value)} maxLength={500} className={input} /></label>
              </>
            )}
            <label className={label}>বিস্তারিত {d.type === 'report' && '*'}<textarea value={d.note} onChange={(e) => set('note', e.target.value)} maxLength={1000} rows={4} className={input} /></label>
          </>
        )}

        {step === 2 && (
          <div className="space-y-3 text-sm">
            <p>অবস্থান দিলে মডারেটর সহজে যাচাই করতে পারেন। আপনার অবস্থান শুধু এই অবদানের সঙ্গে সংরক্ষিত হবে।</p>
            <button type="button" onClick={locate} className="inline-flex items-center gap-1 rounded-chip border border-line px-3 py-2 font-medium text-secondary">
              <LocateFixed className="h-4 w-4" aria-hidden /> আমার বর্তমান অবস্থান ব্যবহার করুন
            </button>
            {d.lat !== null && d.lon !== null && (
              <p>অবস্থান: <span className="font-en">{d.lat}, {d.lon}</span> <button type="button" onClick={() => { set('lat', null); set('lon', null); }} className="text-secondary underline">মুছুন</button></p>
            )}
          </div>
        )}

        {step === 3 && (
          <>
            <label className={label}>উৎসের লিংক (প্রতিটি নতুন লাইনে, সর্বোচ্চ ৫টি)
              <textarea value={d.evidence} onChange={(e) => set('evidence', e.target.value)} rows={3} placeholder="https://…" className={input} />
              <span className="text-xs text-muted">সরকারি পোর্টাল বা প্রতিষ্ঠানের নিজস্ব ওয়েবসাইট সবচেয়ে ভালো। সার্চ রেজাল্টের লিংক গ্রহণযোগ্য নয়।</span>
            </label>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" checked={d.confirmed} onChange={(e) => set('confirmed', e.target.checked)} className="mt-1" />
              আমি নিশ্চিত করছি যে তথ্যগুলো আমার জানামতে সঠিক এবং এতে কারও ব্যক্তিগত তথ্য নেই।
            </label>
          </>
        )}
      </div>

      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
      <div className="mt-4 flex flex-wrap justify-between gap-2">
        <button type="button" disabled={step === 0} onClick={() => setStep(step - 1)} className="rounded-chip border border-line px-4 py-2 disabled:opacity-40">আগের ধাপ</button>
        <div className="flex gap-2">
          {step === 3 && <button type="button" disabled={busy} onClick={() => submit(true)} className="rounded-chip border border-line px-4 py-2">খসড়া হিসেবে রাখুন</button>}
          {step < 3 ? (
            <button type="button" disabled={!valid[step] || (step === 0 && needsTarget && !targetPlace && !targetArea)} onClick={() => setStep(step + 1)}
              className="rounded-chip bg-primary px-4 py-2 font-semibold text-on-primary disabled:opacity-40">পরের ধাপ</button>
          ) : (
            <button type="button" disabled={!valid[3] || busy} onClick={() => submit(false)} className="rounded-chip bg-primary px-4 py-2 font-semibold text-on-primary disabled:opacity-40">জমা দিন</button>
          )}
        </div>
      </div>
    </div>
  );
}
