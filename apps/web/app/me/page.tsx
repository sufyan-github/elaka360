import Link from 'next/link';
import { redirect } from 'next/navigation';
import type { Metadata } from 'next';
import type { Contribution, Review } from '@elaka360/shared';
import { CONTRIBUTION_STATUS_LABEL, formatDate, formatNumber, toBnDigits } from '@elaka360/shared';
import { authedGet, currentUser } from '@/lib/session';
import { Card, EmptyState, Section, StatTile } from '@/components/ui';
import { AccountActions } from './AccountActions';

export const dynamic = 'force-dynamic';   // personal page: never cached
export const metadata: Metadata = { title: 'আমার প্রোফাইল', robots: { index: false } };

const TYPE_LABEL: Record<string, string> = {
  new_place: 'নতুন স্থান', new_business: 'নতুন ব্যবসা', new_tourist_spot: 'নতুন পর্যটন স্থান', area_info: 'এলাকার তথ্য',
  photo: 'ছবি', correction: 'সংশোধন', report: 'রিপোর্ট',
};

export default async function MePage() {
  const me = await currentUser();
  if (!me) redirect('/login?next=/me');
  const [contribs, reviews] = await Promise.all([
    authedGet<{ items: Contribution[] }>('/v1/me/contributions'),
    authedGet<{ items: Review[] }>('/v1/me/reviews'),
  ]);
  const items = contribs?.items ?? [];
  const approved = items.filter((c) => c.status === 'approved').length;

  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{me.name}</h1>
      <p className="text-sm text-muted">{me.phone ? toBnDigits(me.phone.replace('+88', '')) : ''} · সদস্য {formatDate(me.created_at)} থেকে</p>
      {me.permissions.length > 0 && (
        <p className="mt-2 text-sm">আপনার স্টাফ অ্যাক্সেস আছে — অ্যাডমিন প্যানেল আলাদা ঠিকানায় চলে।</p>
      )}

      <div className="mt-4 grid grid-cols-3 gap-3">
        <StatTile label="পয়েন্ট" value={formatNumber(me.points)} />
        <StatTile label="অবদান" value={formatNumber(items.length)} />
        <StatTile label="অনুমোদিত" value={formatNumber(approved)} />
      </div>

      <Section title="আমার অবদান" action={{ href: '/contribute', label: 'নতুন অবদান' }}>
        {items.length ? (
          <Card className="divide-y divide-line">
            {items.map((c) => (
              <div key={c.id} className="flex items-start justify-between gap-3 px-4 py-3 text-sm">
                <div className="min-w-0">
                  <div className="font-semibold">{TYPE_LABEL[c.type] ?? c.type}{typeof c.payload.name_bn === 'string' ? ` — ${c.payload.name_bn}` : c.target_place_slug ? ` — ${c.target_place_slug}` : ''}</div>
                  <div className="text-xs text-muted">{formatDate(c.created_at)}{c.reviewer_note ? ` · মডারেটর: ${c.reviewer_note}` : ''}</div>
                </div>
                <span className="shrink-0 rounded-full border border-line px-2 py-0.5 text-xs">{CONTRIBUTION_STATUS_LABEL[c.status].bn}</span>
              </div>
            ))}
          </Card>
        ) : (
          <EmptyState title="এখনো কোনো অবদান নেই" body="আপনার এলাকার কোনো স্থান বা ভুল তথ্যের সংশোধন যোগ করুন।" />
        )}
      </Section>

      <Section title="আমার রিভিউ">
        {reviews?.items.length ? (
          <Card className="divide-y divide-line">
            {reviews.items.map((r) => (
              <Link key={r.id} href={`/p/${r.place_slug}#reviews`} className="block px-4 py-3 text-sm">
                <span className="font-semibold">{r.place_slug}</span> · {toBnDigits(r.rating)}/৫ · <span className="text-muted">{formatDate(r.created_at)}</span>
                {r.body && <span className="mt-1 block text-muted">{r.body}</span>}
              </Link>
            ))}
          </Card>
        ) : (
          <p className="text-sm text-muted">এখনো কোনো রিভিউ দেননি।</p>
        )}
      </Section>

      <Section title="অ্যাকাউন্ট">
        <AccountActions name={me.name} deletionRequested={me.deletion_requested_at} />
      </Section>
    </div>
  );
}
