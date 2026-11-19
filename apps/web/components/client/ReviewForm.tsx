'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Star } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { localePath } from '@/lib/links';
import { digits } from '@/lib/locale';

const ERROR_KEY = { 401: 'error401', 409: 'error409', 429: 'error429' } as const;

export function ReviewForm({ slug }: { slug: string }) {
  const t = useTranslations('Review');
  const locale = useLocale();
  const router = useRouter();
  const [rating, setRating] = useState(0);
  const [body, setBody] = useState('');
  const [state, setState] = useState<{ kind: 'idle' | 'busy' | 'done' | 'error'; msg?: string; status?: number }>({ kind: 'idle' });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!rating) return setState({ kind: 'error', msg: t('pickRating') });
    setState({ kind: 'busy' });
    const res = await fetch(`/api/u/places/${slug}/reviews`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rating, body: body.trim() || null }),
    });
    if (res.ok) {
      setState({ kind: 'done' });
      router.refresh();
    } else {
      const key = ERROR_KEY[res.status as keyof typeof ERROR_KEY];
      setState({ kind: 'error', status: res.status, msg: key ? t(key) : t('failed') });
    }
  }

  if (state.kind === 'done') return <p role="status" className="text-sm text-secondary">{t('thanks')}</p>;
  return (
    <form onSubmit={submit} className="space-y-3">
      <fieldset>
        <legend className="text-sm font-medium">{t('rating')}</legend>
        <div className="mt-1 flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" onClick={() => setRating(n)} aria-label={t('stars', { count: digits(n, locale), n })} aria-pressed={rating === n}
              className="grid h-10 w-10 place-items-center rounded-chip border border-line">
              <Star className={`h-5 w-5 ${n <= rating ? 'fill-accent text-accent' : 'text-muted'}`} aria-hidden />
            </button>
          ))}
        </div>
      </fieldset>
      <label className="block text-sm">
        <span className="font-medium">{t('comment')}</span>
        <textarea value={body} onChange={(e) => setBody(e.target.value)} maxLength={2000} rows={3}
          className="mt-1 w-full rounded-chip border border-line bg-surface p-2" />
        <span className="text-xs text-muted">{digits(body.length, locale)}/{digits(2000, locale)} · {t('privacyHint')}</span>
      </label>
      {state.kind === 'error' && (
        <p role="alert" className="text-sm text-danger">
          {state.msg} {state.status === 401 && <Link href={`/login?next=${encodeURIComponent(localePath(locale, `/p/${slug}`))}`} className="underline">{t('signIn')}</Link>}
        </p>
      )}
      <button type="submit" disabled={state.kind === 'busy'} className="rounded-chip bg-primary px-4 py-2 text-sm font-semibold text-on-primary disabled:opacity-60">
        {t('submit')}
      </button>
    </form>
  );
}
