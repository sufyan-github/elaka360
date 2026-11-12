import { redirect } from 'next/navigation';
import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Contribution, Review } from '@elaka360/shared';
import { CONTRIBUTION_STATUS_LABEL, formatDate, formatNumber } from '@elaka360/shared';
import { authedGet, currentUser } from '@/lib/session';
import { asLocale, digits } from '@/lib/locale';
import { localePath } from '@/lib/links';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, EmptyState, Section, StatTile } from '@/components/ui';
import { AccountActions } from './AccountActions';

export const dynamic = 'force-dynamic';   // personal page: never cached
type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Me' });
  return { title: t('title'), robots: { index: false }, alternates: localeAlternates(locale, '/me') };
}

const TYPES = ['new_place', 'new_business', 'new_tourist_spot', 'area_info', 'photo', 'correction', 'report'] as const;

export default async function MePage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Me');
  const me = await currentUser();
  if (!me) redirect(`${localePath(locale, '/login')}?next=${localePath(locale, '/me')}`);
  const typeLabel = (type: string) => (TYPES.includes(type as never) ? t(`type.${type as (typeof TYPES)[number]}`) : type);
  const [contribs, reviews] = await Promise.all([
    authedGet<{ items: Contribution[] }>('/v1/me/contributions'),
    authedGet<{ items: Review[] }>('/v1/me/reviews'),
  ]);
  const items = contribs?.items ?? [];
  const approved = items.filter((c) => c.status === 'approved').length;

  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{me.name}</h1>
      <p className="text-sm text-muted">{me.phone ? digits(me.phone.replace('+88', ''), locale) : ''} · {t('memberSince', { date: formatDate(me.created_at, locale) })}</p>
      {me.permissions.length > 0 && (
        <p className="mt-2 text-sm">{t('staff')}</p>
      )}

      <div className="mt-4 grid grid-cols-3 gap-3">
        <StatTile label={t('points')} value={formatNumber(me.points, locale)} />
        <StatTile label={t('contributions')} value={formatNumber(items.length, locale)} />
        <StatTile label={t('approved')} value={formatNumber(approved, locale)} />
      </div>

      <Section title={t('myContributions')} action={{ href: '/contribute', label: t('newContribution') }}>
        {items.length ? (
          <Card className="divide-y divide-line">
            {items.map((c) => (
              <div key={c.id} className="flex items-start justify-between gap-3 px-4 py-3 text-sm">
                <div className="min-w-0">
                  <div className="font-semibold">{typeLabel(c.type)}{typeof c.payload.name_bn === 'string' ? ` — ${c.payload.name_bn}` : c.target_place_slug ? ` — ${c.target_place_slug}` : ''}</div>
                  <div className="text-xs text-muted">{formatDate(c.created_at, locale)}{c.reviewer_note ? ` · ${t('moderator', { note: c.reviewer_note })}` : ''}</div>
                </div>
                <span className="shrink-0 rounded-full border border-line px-2 py-0.5 text-xs">{CONTRIBUTION_STATUS_LABEL[c.status]?.[locale] ?? c.status}</span>
              </div>
            ))}
          </Card>
        ) : (
          <EmptyState title={t('emptyTitle')} body={t('emptyBody')} />
        )}
      </Section>

      <Section title={t('myReviews')}>
        {reviews?.items.length ? (
          <Card className="divide-y divide-line">
            {reviews.items.map((r) => (
              <Link key={r.id} href={`/p/${r.place_slug}#reviews`} className="block px-4 py-3 text-sm">
                <span className="font-semibold">{r.place_slug}</span> · {digits(r.rating, locale)}/{digits(5, locale)} · <span className="text-muted">{formatDate(r.created_at, locale)}</span>
                {r.body && <span className="mt-1 block text-muted">{r.body}</span>}
              </Link>
            ))}
          </Card>
        ) : (
          <p className="text-sm text-muted">{t('noReviews')}</p>
        )}
      </Section>

      <Section title={t('account')}>
        <AccountActions name={me.name} deletionRequested={me.deletion_requested_at} />
      </Section>
    </div>
  );
}
