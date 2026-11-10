'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { formatDate } from '@elaka360/shared';

export function AccountActions({ name, deletionRequested }: { name: string; deletionRequested: string | null }) {
  const router = useRouter();
  const [value, setValue] = useState(name);
  const [msg, setMsg] = useState<string | null>(null);

  async function call(url: string, method: string, body?: unknown) {
    const res = await fetch(url, { method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
    if (!res.ok) setMsg('কাজটি করা যায়নি। আবার চেষ্টা করুন।');
    return res.ok;
  }

  return (
    <div className="space-y-5 rounded-card border border-line bg-surface p-4 text-sm">
      <form onSubmit={async (e) => { e.preventDefault(); if (await call('/api/u/me', 'PATCH', { name: value })) { setMsg('নাম হালনাগাদ হয়েছে।'); router.refresh(); } }} className="flex flex-wrap items-end gap-2">
        <label className="min-w-0 flex-1">
          <span className="font-medium">প্রদর্শিত নাম</span>
          <input value={value} onChange={(e) => setValue(e.target.value)} minLength={2} maxLength={80} className="mt-1 w-full rounded-chip border border-line bg-surface px-3 py-2" />
        </label>
        <button className="rounded-chip border border-line px-4 py-2 font-medium">সংরক্ষণ</button>
      </form>

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={async () => { await call('/api/auth/logout', 'POST'); router.replace('/'); router.refresh(); }} className="rounded-chip border border-line px-4 py-2 font-medium">সাইন আউট</button>
        <button type="button" onClick={async () => { await call('/api/auth/logout?all=1', 'POST'); router.replace('/'); router.refresh(); }} className="rounded-chip border border-line px-4 py-2 font-medium">সব ডিভাইস থেকে সাইন আউট</button>
      </div>

      <div className="border-t border-line pt-4">
        {deletionRequested ? (
          <p>
            {formatDate(deletionRequested)} তারিখে অ্যাকাউন্ট মুছে ফেলার অনুরোধ করেছেন।{' '}
            <button type="button" onClick={async () => { if (await call('/api/u/me/deletion-request', 'DELETE')) router.refresh(); }} className="text-secondary underline">অনুরোধ বাতিল করুন</button>
          </p>
        ) : (
          <button type="button" className="text-danger underline"
            onClick={async () => { if (window.confirm('আপনার অ্যাকাউন্ট মুছে ফেলার অনুরোধ পাঠাবেন? দল যাচাই করে মুছে ফেলবে।') && (await call('/api/u/me/deletion-request', 'POST'))) router.refresh(); }}>
            অ্যাকাউন্ট মুছে ফেলার অনুরোধ
          </button>
        )}
      </div>
      {msg && <p role="status" className="text-muted">{msg}</p>}
    </div>
  );
}
