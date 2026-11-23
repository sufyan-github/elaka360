'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

/** Approve / needs changes / reject, with a required note the contributor sees. */
export function Decision({ id }: { id: number }) {
  const t = useTranslations('Moderate');
  const router = useRouter();
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: 'approved' | 'needs_changes' | 'rejected') {
    setBusy(true); setError(null);
    const res = await fetch(`/api/u/mod/contributions/${id}/decision`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, note: note.trim() }),
    });
    setBusy(false);
    if (!res.ok) {
      const p = await res.json().catch(() => ({}));
      return setError(p.detail ?? t('failed'));
    }
    router.refresh();
  }

  return (
    <div className="mt-3 space-y-2 border-t border-line pt-3">
      <label className="block text-xs font-medium">{t('note')}
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={1000} className="mt-1 w-full rounded-chip border border-line bg-surface px-3 py-2 text-sm" />
      </label>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy || note.trim().length < 3} onClick={() => decide('approved')} className="rounded-chip bg-primary px-3 py-1.5 font-semibold text-on-primary disabled:opacity-40">{t('approve')}</button>
        <button type="button" disabled={busy || note.trim().length < 3} onClick={() => decide('needs_changes')} className="rounded-chip border border-line px-3 py-1.5 disabled:opacity-40">{t('needsChanges')}</button>
        <button type="button" disabled={busy || note.trim().length < 3} onClick={() => decide('rejected')} className="rounded-chip border border-danger px-3 py-1.5 text-danger disabled:opacity-40">{t('reject')}</button>
      </div>
      {error && <p role="alert" className="text-xs text-danger">{error}</p>}
    </div>
  );
}
