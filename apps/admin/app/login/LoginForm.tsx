'use client';

import { useState } from 'react';
import { formatNumber, toBnDigits } from '@elaka360/shared';

type Step = 'phone' | 'code';

async function post(path: string, body: unknown) {
  const res = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) throw new Error(String(data.detail ?? data.title ?? `HTTP ${res.status}`));
  return data;
}

export function LoginForm({ next }: { next: string }) {
  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [devCode, setDevCode] = useState<string | null>(null);
  const [expires, setExpires] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const d = await post('/api/auth/otp/request', { phone });
      setDevCode(typeof d.dev_code === 'string' ? d.dev_code : null);
      setExpires(typeof d.expires_in === 'number' ? d.expires_in : null);
      setStep('code');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post('/api/auth/otp/verify', { phone, code });
      window.location.assign(next);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div>
      {step === 'phone' ? (
        <form onSubmit={requestCode} className="space-y-4">
          <div>
            <label htmlFor="phone" className="mb-1 block text-sm font-medium">মোবাইল নম্বর <span className="font-en text-muted">· Mobile</span></label>
            <input id="phone" name="phone" className="input font-en" inputMode="tel" autoComplete="tel" required placeholder="01XXXXXXXXX"
              value={phone} onChange={(e) => setPhone(e.target.value)} aria-describedby={error ? 'login-error' : undefined} autoFocus />
          </div>
          <button type="submit" className="btn btn-primary w-full" disabled={busy || phone.trim().length < 11}>
            {busy ? 'পাঠানো হচ্ছে…' : 'কোড পাঠান'}
          </button>
        </form>
      ) : (
        <form onSubmit={verify} className="space-y-4">
          <p className="text-sm text-muted">
            <span className="font-en">{phone}</span> নম্বরে ৬ সংখ্যার কোড পাঠানো হয়েছে
            {expires ? ` (মেয়াদ ${formatNumber(Math.round(expires / 60))} মিনিট)` : ''}।
          </p>
          {devCode && (
            <p role="status" className="rounded-chip border border-dashed border-accent bg-tint px-3 py-2 text-sm">
              ডেভেলপমেন্ট কোড <span className="font-en">(dev SMS provider)</span>: <strong className="font-en tracking-widest">{devCode}</strong>
              <span className="sr-only"> ({toBnDigits(devCode)})</span>
            </p>
          )}
          <div>
            <label htmlFor="code" className="mb-1 block text-sm font-medium">কোড <span className="font-en text-muted">· Code</span></label>
            <input id="code" name="code" className="input font-en tracking-widest" inputMode="numeric" autoComplete="one-time-code" required
              pattern="[0-9০-৯]{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} autoFocus
              aria-describedby={error ? 'login-error' : undefined} />
          </div>
          <button type="submit" className="btn btn-primary w-full" disabled={busy || code.trim().length !== 6}>
            {busy ? 'যাচাই হচ্ছে…' : 'সাইন ইন'}
          </button>
          <button type="button" className="btn btn-outline w-full" onClick={() => { setStep('phone'); setCode(''); setDevCode(null); setError(null); }}>
            নম্বর বদলান
          </button>
        </form>
      )}
      {error && <p id="login-error" role="alert" className="mt-4 rounded-chip bg-danger-tint px-3 py-2 text-sm text-danger">{error}</p>}
    </div>
  );
}
