import Link from 'next/link';
import { formatNumber, toBnDigits } from '@elaka360/shared';
import { decideReport } from '../actions';
import { ActionForm, SubmitButton } from '@/components/ActionForm';
import { Card, EmptyState, ErrorPanel, PageHeader, StatusChip, formatDateTime } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import type { ReviewReportRow } from '@/lib/types';

export const metadata = { title: 'রিভিউ রিপোর্ট' };

const SITE = process.env.PUBLIC_SITE_URL ?? 'http://localhost:3000';
const TABS = [['open', 'খোলা'], ['upheld', 'বহাল'], ['dismissed', 'খারিজ']] as const;

export default async function ReviewReportsPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { ok } = await access('reviews.moderate');
  if (!ok) return <Forbidden perm="reviews.moderate" />;
  const { status: raw } = await searchParams;
  const status = TABS.some(([k]) => k === raw) ? raw! : 'open';
  const r = await apiTry<{ items: ReviewReportRow[] }>(`/v1/admin/review-reports?status=${status}`);
  return (
    <>
      <PageHeader title="রিভিউ রিপোর্ট" en="Review reports">
        {r.data && <span className="text-sm text-muted">{formatNumber(r.data.items.length)}টি</span>}
      </PageHeader>
      <nav aria-label="অবস্থা" className="mb-4 flex gap-2">
        {TABS.map(([k, l]) => (
          <Link key={k} href={`/review-reports?status=${k}`} aria-current={status === k ? 'page' : undefined} className={`btn ${status === k ? 'btn-primary' : 'btn-outline'}`}>{l}</Link>
        ))}
      </nav>
      {r.error ? <ErrorPanel error={r.error} /> : !r.data.items.length ? (
        <Card><EmptyState title="কোনো রিপোর্ট নেই" hint={status === 'open' ? 'এই মুহূর্তে কোনো খোলা রিপোর্ট নেই।' : undefined} /></Card>
      ) : (
        <ul className="space-y-3">
          {r.data.items.map((x) => (
            <li key={x.id}>
              <Card>
                <div className="grid gap-4 p-4 md:grid-cols-[1fr_auto]">
                  <div className="min-w-0 space-y-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <a className="font-semibold text-secondary hover:underline" href={`${SITE}/p/${x.place_slug}`} target="_blank" rel="noopener noreferrer">{x.place_name} ↗</a>
                      <span aria-label={`রেটিং ${x.rating}`}>{'★'.repeat(x.rating)}<span className="text-muted">{'★'.repeat(Math.max(0, 5 - x.rating))}</span> ({toBnDigits(x.rating)}/৫)</span>
                      <StatusChip status={x.status} />
                      {x.review_status !== 'active' && <span className="text-xs text-muted">রিভিউ লুকানো ({x.review_status})</span>}
                    </div>
                    <blockquote className="rounded-chip border-l-4 border-line bg-bg px-3 py-2">{x.body ?? <span className="text-muted">(লেখা নেই)</span>}</blockquote>
                    <p className="text-muted">লেখক: {x.author_name} · রিপোর্টকারী: {x.reporter_name} · {formatDateTime(x.created_at)}</p>
                    <p><span className="text-muted">রিপোর্টের কারণ:</span> {x.reason ?? '—'}</p>
                  </div>
                  {x.status === 'open' && (
                    <ActionForm action={decideReport.bind(null, x.id)} className="flex flex-col gap-2 md:w-44">
                      <SubmitButton variant="danger" name="decision" value="uphold" confirm="রিপোর্ট বহাল রাখলে রিভিউটি লুকানো হবে এবং রেটিং পুনর্গণনা হবে। নিশ্চিত?">বহাল · Uphold</SubmitButton>
                      <SubmitButton variant="outline" name="decision" value="dismiss" confirm="রিপোর্টটি খারিজ করবেন? রিভিউ দৃশ্যমান থাকবে।">খারিজ · Dismiss</SubmitButton>
                    </ActionForm>
                  )}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
