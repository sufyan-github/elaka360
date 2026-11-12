'use client';

import { useState } from 'react';
// `next` is already a full path in the right locale (e.g. /en/me), so the plain Next router is used here.
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { digits } from '@/lib/locale';

type Step = { kind: 'phone' } | { kind: 'code'; devCode?: string };

function messageKey(status: number, detail?: string) {
  if (status === 429) return 'error429';
  if (status === 503) return 'error503';
  if (status === 401) return detail?.includes('wrong') ? 'wrongCode' : 'expiredCode';
  if (status === 400) return 'error400';
  return 'errorGeneric';
}

export function LoginForm({ next }: { next: string }) {
  const t = useTranslations('Login');
  const locale = useLocale();
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
    if (!res.ok) return setError(t(messageKey(res.status, json.detail)));
    setStep({ kind: 'code', devCode: json.dev_code });
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    const { res, json } = await post('/api/auth/verify', { phone, code, name: name.trim() || undefined });
    setBusy(false);
    if (!res.ok) return setError(t(messageKey(res.status, json.detail)));
    router.replace(next);
    router.refresh();
  }

  const input = 'mt-1 w-full rounded-chip border border-line bg-surface px-3 py-2.5 text-base';
  return (
    <div className="mt-6 rounded-card border border-line bg-surface p-4 shadow-card">
      {step.kind === 'phone' ? (
        <form onSubmit={requestCode} className="space-y-4">
          <label className="block text-sm font-medium">
            {t('phone')}
            <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="tel" required placeholder="01XXXXXXXXX" className={input} />
          </label>
          <button disabled={busy} className="w-full rounded-chip bg-primary py-2.5 font-semibold text-on-primary disabled:opacity-60">{t('sendCode')}</button>
        </form>
      ) : (
        <form onSubmit={verify} className="space-y-4">
          <p className="text-sm">{t('enterCode', { phone: digits(phone, locale) })}</p>
          {step.devCode && (
            <p className="rounded-chip bg-warning-tint p-2 text-xs text-warning">{t('devCode', { code: step.devCode })}</p>
          )}
          <label className="block text-sm font-medium">
            {t('code')}
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" required maxLength={6} className={input} />
          </label>
          <label className="block text-sm font-medium">
            {t('name')}
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} autoComplete="name" className={input} />
          </label>
          <button disabled={busy} className="w-full rounded-chip bg-primary py-2.5 font-semibold text-on-primary disabled:opacity-60">{t('signIn')}</button>
          <button type="button" onClick={() => { setStep({ kind: 'phone' }); setCode(''); }} className="w-full text-sm text-secondary underline">{t('changeNumber')}</button>
        </form>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    </div>
  );
}
