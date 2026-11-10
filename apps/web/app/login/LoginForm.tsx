'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { toBnDigits } from '@elaka360/shared';

type Step = { kind: 'phone' } | { kind: 'code'; devCode?: string };

function message(status: number, detail?: string): string {
  if (status === 429) return 'অনেকবার চেষ্টা হয়েছে। কিছুক্ষণ পরে আবার চেষ্টা করুন।';
  if (status === 503) return 'এই মুহূর্তে এসএমএস পাঠানো যাচ্ছে না। পরে চেষ্টা করুন।';
  if (status === 401) return detail?.includes('wrong') ? 'কোডটি সঠিক নয়।' : 'কোডের মেয়াদ শেষ বা অনেকবার ভুল হয়েছে — নতুন কোড নিন।';
  if (status === 400) return 'সঠিক বাংলাদেশি মোবাইল নম্বর লিখুন (যেমন ০১৭১২৩৪৫৬৭৮)।';
  return 'কিছু একটা সমস্যা হয়েছে। আবার চেষ্টা করুন।';
}

export function LoginForm({ next }: { next: string }) {
  const router = useRouter();
  const [step, setStep] = useState<Step>({ kind: 'phone' });
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function post(url: string, body: unknown) {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const json = await res.json().catch(() => ({}));
    return { res, json };
  }

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    const { res, json } = await post('/api/auth/otp', { phone });
    setBusy(false);
    if (!res.ok) return setError(message(res.status, json.detail));
    setStep({ kind: 'code', devCode: json.dev_code });
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    const { res, json } = await post('/api/auth/verify', { phone, code, name: name.trim() || undefined });
    setBusy(false);
    if (!res.ok) return setError(message(res.status, json.detail));
    router.replace(next);
    router.refresh();
  }

  const input = 'mt-1 w-full rounded-chip border border-line bg-surface px-3 py-2.5 text-base';
  return (
    <div className="mt-6 rounded-card border border-line bg-surface p-4 shadow-card">
      {step.kind === 'phone' ? (
        <form onSubmit={requestCode} className="space-y-4">
          <label className="block text-sm font-medium">
            মোবাইল নম্বর
            <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="tel" required placeholder="01XXXXXXXXX" className={input} />
          </label>
          <button disabled={busy} className="w-full rounded-chip bg-primary py-2.5 font-semibold text-on-primary disabled:opacity-60">কোড পাঠান</button>
        </form>
      ) : (
        <form onSubmit={verify} className="space-y-4">
          <p className="text-sm">{toBnDigits(phone)} নম্বরে পাঠানো কোডটি লিখুন।</p>
          {step.devCode && (
            <p className="rounded-chip bg-warning-tint p-2 text-xs text-warning">ডেভেলপমেন্ট সার্ভার: কোড {step.devCode} (প্রকৃত সার্ভারে এসএমএসে যাবে)</p>
          )}
          <label className="block text-sm font-medium">
            ৬-অঙ্কের কোড
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" required maxLength={6} className={input} />
          </label>
          <label className="block text-sm font-medium">
            আপনার নাম (প্রথমবার, ঐচ্ছিক)
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} autoComplete="name" className={input} />
          </label>
          <button disabled={busy} className="w-full rounded-chip bg-primary py-2.5 font-semibold text-on-primary disabled:opacity-60">সাইন ইন</button>
          <button type="button" onClick={() => { setStep({ kind: 'phone' }); setCode(''); }} className="w-full text-sm text-secondary underline">নম্বর বদলান / নতুন কোড</button>
        </form>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    </div>
  );
}
