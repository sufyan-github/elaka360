import Link from 'next/link';
import type { ContributionStatus } from '@elaka360/shared';
import { CONTRIBUTION_STATUS_LABEL, formatNumber } from '@elaka360/shared';
import { Card, Chip, EmptyState, ErrorPanel, FilterBar, FilterField, PageHeader, Pager, TableWrap, formatDateTime } from '@/components/ui';
import { apiTry, qs } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import { CONTRIBUTION_TYPE_LABEL } from '@/lib/labels';
import type { ContributionRow, Page } from '@/lib/types';

export const metadata = { title: 'মডারেশন' };

const STATUSES: ContributionStatus[] = ['new', 'in_review', 'needs_changes', 'approved', 'rejected'];
const PRIORITY: Record<string, string> = { urgent: 'জরুরি', high: 'উচ্চ', normal: 'সাধারণ', low: 'নিম্ন' };

type SP = { status?: string; type?: string; cursor?: string };

export default async function ModerationPage({ searchParams }: { searchParams: Promise<SP> }) {
  const { ok } = await access('contributions.moderate');
  if (!ok) return <Forbidden perm="contributions.moderate" />;
  const sp = await searchParams;
  const r = await apiTry<Page<ContributionRow>>(`/v1/admin/contributions${qs({ status: sp.status, type: sp.type, cursor: sp.cursor, limit: 50 })}`);
  return (
    <>
      <PageHeader title="মডারেশন" en="Contributions queue">
        {r.data && <span className="text-sm text-muted">মোট {formatNumber(r.data.total)}টি</span>}
      </PageHeader>
      <FilterBar action="/moderation" resetHref="/moderation">
        <FilterField label="অবস্থা" htmlFor="status">
          <select id="status" name="status" defaultValue={sp.status ?? ''} className="input">
            <option value="">সব</option>
            {STATUSES.map((s) => <option key={s} value={s}>{CONTRIBUTION_STATUS_LABEL[s].bn} ({CONTRIBUTION_STATUS_LABEL[s].en})</option>)}
          </select>
        </FilterField>
        <FilterField label="ধরন" htmlFor="type">
          <select id="type" name="type" defaultValue={sp.type ?? ''} className="input">
            <option value="">সব</option>
            {Object.entries(CONTRIBUTION_TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v.bn} ({v.en})</option>)}
          </select>
        </FilterField>
      </FilterBar>
      <p className="mb-3 text-xs text-muted">আপনার এলাকার পরিধির মধ্যে; জরুরি আগে, তারপর পুরনো আগে।</p>
      <Card>
        {r.error ? <div className="p-4"><ErrorPanel error={r.error} /></div> : !r.data.items.length ? (
          <EmptyState title="কোনো অবদান নেই" hint="এই ফিল্টারে মডারেশনের জন্য কিছু অপেক্ষমাণ নেই।" />
        ) : (
          <>
            <TableWrap>
              <table className="table">
                <thead><tr><th scope="col">#</th><th scope="col">ধরন</th><th scope="col">অবস্থা</th><th scope="col">অগ্রাধিকার</th><th scope="col">বিষয়</th><th scope="col">জমাদাতা</th><th scope="col">এলাকা</th><th scope="col">জমার সময়</th></tr></thead>
                <tbody>
                  {r.data.items.map((c) => {
                    const subject = c.target_place_name ?? (typeof c.payload.name_bn === 'string' ? c.payload.name_bn : null);
                    return (
                      <tr key={c.id}>
                        <td><Link className="font-en font-medium text-secondary hover:underline" href={`/moderation/${c.id}`}>#{c.id}</Link></td>
                        <td className="whitespace-nowrap">{CONTRIBUTION_TYPE_LABEL[c.type]?.bn ?? c.type}</td>
                        <td><Chip tone={c.status === 'rejected' ? 'danger' : c.status === 'approved' ? 'tint' : 'line'}>{CONTRIBUTION_STATUS_LABEL[c.status]?.bn ?? c.status}</Chip></td>
                        <td>{c.priority === 'urgent' || c.priority === 'high' ? <Chip tone="danger">{PRIORITY[c.priority]}</Chip> : PRIORITY[c.priority] ?? c.priority}</td>
                        <td><Link className="hover:underline" href={`/moderation/${c.id}`}>{subject ?? <span className="text-muted">—</span>}</Link></td>
                        <td className="text-sm">{c.submitter_name} <span className="font-en text-xs text-muted">#{c.submitter_id}</span></td>
                        <td className="font-en text-xs">{c.area_path ?? '—'}</td>
                        <td className="whitespace-nowrap text-xs">{formatDateTime(c.created_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableWrap>
            <Pager basePath="/moderation" params={sp} nextCursor={r.data.next_cursor} hasCursor={!!sp.cursor} />
          </>
        )}
      </Card>
    </>
  );
}
