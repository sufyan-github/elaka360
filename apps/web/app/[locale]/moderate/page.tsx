import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { ExternalLink } from 'lucide-react';
import { formatDate, formatNumber, type Contribution } from '@elaka360/shared';
import { asLocale } from '@/lib/locale';
import { authedGet, currentUser } from '@/lib/session';
import { Link } from '@/i18n/navigation';
import { Card } from '@/components/ui';
import { Decision } from './Decision';

export const dynamic = 'force-dynamic';

type Item = Contribution & { contributor_name: string; area_path: string | null; area_name: string | null };
type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ status?: string }> };
const STATUSES = ['new', 'needs_changes', 'approved', 'rejected'] as const;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const t = await getTranslations({ locale: asLocale((await params).locale), namespace: 'Moderate' });
  return { title: t('title'), robots: { index: false } };
}

/** Staff review queue for submissions (edge API /v1/mod/contributions). Nothing is published until a release. */
export default async function ModeratePage({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Moderate');
  const tw = await getTranslations('Wizard');
  const me = await currentUser();
  if (!me) return <p className="pt-6"><Link href="/login?next=/moderate" className="text-secondary underline">{t('signIn')}</Link></p>;
  if (!me.permissions.includes('contributions.moderate')) return <p className="pt-6">{t('notAllowed')}</p>;
  const sp = await searchParams;
  const status = STATUSES.includes(sp.status as never) ? sp.status! : 'new';
  const data = await authedGet<{ items: Item[]; counts: Record<string, number> }>(`/v1/mod/contributions?status=${status}&limit=50`);
  const items = data?.items ?? [];

  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p className="mt-1 text-sm text-muted">{t('intro')}</p>
      <nav className="mt-4 flex flex-wrap gap-2 text-sm">
        {STATUSES.map((s) => (
          <Link key={s} href={`/moderate?status=${s}`} className={`rounded-full border px-3 py-1 ${s === status ? 'border-primary bg-primary text-on-primary' : 'border-line'}`}>
            {t(`status.${s}`)} ({formatNumber(data?.counts?.[s] ?? 0, locale)})
          </Link>
        ))}
      </nav>
      {!data && <p className="mt-6 text-sm text-danger">{t('loadFailed')}</p>}
      {data && !items.length && <p className="mt-6 text-sm text-muted">{t('empty')}</p>}
      <div className="mt-4 space-y-4">
        {items.map((c) => (
          <Card key={c.id} className="p-4 text-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-semibold">#{formatNumber(c.id, locale)} · {tw(`type.${c.type}` as never)}</span>
              <span className="text-xs text-muted">{c.contributor_name} · {formatDate(c.created_at, locale)}</span>
            </div>
            {c.area_path && <p className="mt-1"><Link href={`/${c.area_path}`} className="text-secondary underline">{c.area_name ?? c.area_path}</Link> <span className="text-xs text-muted">({c.area_path})</span></p>}
            {c.target_place_slug && <p className="mt-1"><Link href={`/p/${c.target_place_slug}`} className="text-secondary underline">/p/{c.target_place_slug}</Link></p>}
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              {Object.entries(c.payload).map(([k, v]) => (
                <div key={k} className="contents"><dt className="text-muted">{k}</dt><dd className="whitespace-pre-wrap break-words">{Array.isArray(v) ? v.join(', ') : String(v)}</dd></div>
              ))}
            </dl>
            {c.lat !== null && c.lon !== null && (
              <p className="mt-2">
                {t('point')} <span className="font-en">{c.lat}, {c.lon}</span>{' '}
                <a href={`https://www.openstreetmap.org/?mlat=${c.lat}&mlon=${c.lon}#map=16/${c.lat}/${c.lon}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary underline">
                  {t('openMap')} <ExternalLink className="h-3 w-3" aria-hidden /></a>
              </p>
            )}
            {c.evidence.length > 0 && (
              <ul className="mt-2 list-disc pl-5">{c.evidence.map((e) => <li key={e.url}><a href={e.url} target="_blank" rel="noopener noreferrer nofollow" className="break-all text-secondary underline">{e.url}</a></li>)}</ul>
            )}
            {c.reviewer_note && <p className="mt-2 text-xs text-muted">{t('previousNote', { note: c.reviewer_note })}</p>}
            {(c.status === 'new' || c.status === 'needs_changes') && <Decision id={c.id} />}
          </Card>
        ))}
      </div>
    </div>
  );
}
