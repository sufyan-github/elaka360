'use client';

import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { formatDate } from '@elaka360/shared';
import { useRouter } from '@/i18n/navigation';

export function AccountActions({ name, deletionRequested }: { name: string; deletionRequested: string | null }) {
  const t = useTranslations('Account');
  const locale = useLocale();
  const router = useRouter();
  const [value, setValue] = useState(name);
  const [msg, setMsg] = useState<string | null>(null);

  async function call(url: string, method: string, body?: unknown) {
    const res = await fetch(url, { method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
    if (!res.ok) setMsg(t('failed'));
    return res.ok;
  }

  return (
    <div className="space-y-5 rounded-card border border-line bg-surface p-4 text-sm">
      <form onSubmit={async (e) => { e.preventDefault(); if (await call('/api/u/me', 'PATCH', { name: value })) { setMsg(t('nameUpdated')); router.refresh(); } }} className="flex flex-wrap items-end gap-2">
        <label className="min-w-0 flex-1">
          <span className="font-medium">{t('displayName')}</span>
          <input value={value} onChange={(e) => setValue(e.target.value)} minLength={2} maxLength={80} className="mt-1 w-full rounded-chip border border-line bg-surface px-3 py-2" />
        </label>
        <button className="rounded-chip border border-line px-4 py-2 font-medium">{t('save')}</button>
      </form>

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={async () => { await call('/api/auth/logout', 'POST'); router.replace('/'); router.refresh(); }} className="rounded-chip border border-line px-4 py-2 font-medium">{t('signOut')}</button>
        <button type="button" onClick={async () => { await call('/api/auth/logout?all=1', 'POST'); router.replace('/'); router.refresh(); }} className="rounded-chip border border-line px-4 py-2 font-medium">{t('signOutAll')}</button>
      </div>

      <div className="border-t border-line pt-4">
        {deletionRequested ? (
          <p>
            {t('deletionRequested', { date: formatDate(deletionRequested, locale) })}{' '}
            <button type="button" onClick={async () => { if (await call('/api/u/me/deletion-request', 'DELETE')) router.refresh(); }} className="text-secondary underline">{t('cancelDeletion')}</button>
          </p>
        ) : (
          <button type="button" className="text-danger underline"
            onClick={async () => { if (window.confirm(t('confirmDeletion')) && (await call('/api/u/me/deletion-request', 'POST'))) router.refresh(); }}>
            {t('requestDeletion')}
          </button>
        )}
      </div>
      {msg && <p role="status" className="text-muted">{msg}</p>}
    </div>
  );
}
