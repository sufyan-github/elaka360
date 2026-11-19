'use client';

import { useState } from 'react';

async function post(path: string, body: unknown = {}) {
  const res = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) throw new Error(String(data.detail ?? data.title ?? `HTTP ${res.status}`));
  return data;
}

/**
 * Staff sessions must pass two-factor authentication before any admin page (server setting STAFF_REQUIRE_2FA).
 * Shown by the admin layout instead of the app shell until this session is verified.
 */
export function TwoFactorGate({ enrolled, name }: { enrolled: boolean; name: string }) {
  const [setup, setSetup] = useState<{ secret: string; uri: string } | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const codeInput = (
    <div>
      <label htmlFor="totp" className="mb-1 block text-sm font-medium">অথেনটিকেটর কোড <span className="font-en text-muted">· Authenticator code</span></label>
      <input id="totp" className="input font-en tracking-widest" inputMode="text" autoComplete="one-time-code" required maxLength={12}
        value={code} onChange={(e) => setCode(e.target.value)} autoFocus />
    </div>
  );

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <div className="w-full max-w-md rounded-card border border-line bg-surface p-6 shadow-card">
        <h1 className="text-xl font-bold">দুই-ধাপের যাচাই</h1>
        <p className="font-en text-sm text-muted">Two-factor authentication · {name}</p>

        {codes ? (
          <div className="mt-4 space-y-3 text-sm">
            <p>চালু হয়েছে। এই রিকভারি কোডগুলো নিরাপদে রাখুন — প্রতিটি একবারই কাজ করে, এবং আর দেখানো হবে না।</p>
            <ul className="grid grid-cols-2 gap-2 rounded-chip border border-line p-3 font-en">
              {codes.map((c) => <li key={c}><code>{c}</code></li>)}
            </ul>
            <button type="button" className="btn btn-primary w-full" onClick={() => window.location.reload()}>রেখেছি — চালিয়ে যান</button>
          </div>
        ) : enrolled ? (
          <form className="mt-4 space-y-4" onSubmit={(e) => { e.preventDefault(); void run(async () => { await post('/api/auth/2fa/verify', { code }); window.location.reload(); }); }}>
            <p className="text-sm">অথেনটিকেটর অ্যাপের ৬ অঙ্কের কোড বা একটি রিকভারি কোড লিখুন।</p>
            {codeInput}
            <button type="submit" className="btn btn-primary w-full" disabled={busy || code.trim().length < 6}>যাচাই করুন</button>
          </form>
        ) : !setup ? (
          <div className="mt-4 space-y-4 text-sm">
            <p>কর্মীদের অ্যাকাউন্টে দুই-ধাপের যাচাই বাধ্যতামূলক। একটি অথেনটিকেটর অ্যাপ (যেমন Google Authenticator, Aegis, 1Password) লাগবে।</p>
            <button type="button" className="btn btn-primary w-full" disabled={busy}
              onClick={() => void run(async () => { const d = await post('/api/auth/2fa/setup'); setSetup({ secret: String(d.secret), uri: String(d.otpauth_uri) }); })}>
              সেটআপ শুরু করুন
            </button>
          </div>
        ) : (
          <form className="mt-4 space-y-4 text-sm" onSubmit={(e) => { e.preventDefault(); void run(async () => { const d = await post('/api/auth/2fa/enable', { code }); setCodes(d.recovery_codes as string[]); }); }}>
            <p>অ্যাপে এই কী যোগ করুন (অথবা ফোনে লিংকটি খুলুন), তারপর অ্যাপে দেখানো কোড লিখুন।</p>
            <p className="rounded-chip border border-line p-3 text-center font-en text-base tracking-widest break-all" aria-label="Secret key">
              {setup.secret.match(/.{1,4}/g)?.join(' ')}
            </p>
            <a href={setup.uri} className="block text-center text-secondary underline">অথেনটিকেটর অ্যাপে খুলুন</a>
            {codeInput}
            <button type="submit" className="btn btn-primary w-full" disabled={busy || code.trim().length !== 6}>চালু করুন</button>
          </form>
        )}

        {error && <p role="alert" className="mt-4 rounded-chip bg-danger-tint px-3 py-2 text-sm text-danger">{error === 'wrong code' ? 'কোডটি সঠিক নয়।' : error}</p>}
        <form method="post" action="/api/auth/logout" className="mt-4 text-center">
          <button type="submit" className="text-sm text-muted underline">সাইন আউট</button>
        </form>
      </div>
    </main>
  );
}
