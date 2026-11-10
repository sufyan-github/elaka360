import Link from 'next/link';
import { LEVEL_LABEL, formatNumber } from '@elaka360/shared';
import { EligibleSelect, EvidenceSelect, LevelSelect } from '@/components/filters';
import { Card, EmptyState, ErrorPanel, EvidenceBadge, FilterBar, FilterField, PageHeader, Pager, PublicBadge, TableWrap, formatDateTime } from '@/components/ui';
import { apiTry, qs } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import type { AdminAreaRow, Page } from '@/lib/types';

export const metadata = { title: 'এলাকা' };

type SP = { level?: string; evidence?: string; eligible?: string; q?: string; parent_id?: string; cursor?: string };

export default async function AreasPage({ searchParams }: { searchParams: Promise<SP> }) {
  const { ok } = await access('areas.read');
  if (!ok) return <Forbidden perm="areas.read" />;
  const sp = await searchParams;
  const r = await apiTry<Page<AdminAreaRow>>(`/v1/admin/areas${qs({ level: sp.level, evidence: sp.evidence, eligible: sp.eligible, q: sp.q, parent_id: sp.parent_id, cursor: sp.cursor, limit: 50 })}`);
  return (
    <>
      <PageHeader title="এলাকা" en="Areas">
        {r.data && <span className="text-sm text-muted">মোট {formatNumber(r.data.total)}টি</span>}
      </PageHeader>
      <FilterBar action="/areas" resetHref="/areas">
        <FilterField label="খুঁজুন (নাম)" htmlFor="q" wide><input id="q" name="q" type="search" defaultValue={sp.q} className="input" placeholder="যেমন পবা / Paba" /></FilterField>
        <FilterField label="স্তর" htmlFor="level"><LevelSelect value={sp.level} /></FilterField>
        <FilterField label="প্রমাণ" htmlFor="evidence"><EvidenceSelect value={sp.evidence} /></FilterField>
        <FilterField label="প্রকাশ" htmlFor="eligible"><EligibleSelect value={sp.eligible} /></FilterField>
        {sp.parent_id && <input type="hidden" name="parent_id" value={sp.parent_id} />}
      </FilterBar>
      {sp.parent_id && <p className="mb-3 text-sm">অভিভাবক এলাকা <Link className="font-en text-secondary" href={`/areas/${sp.parent_id}`}>#{sp.parent_id}</Link>-এর অধীন এলাকা দেখানো হচ্ছে।</p>}
      <Card>
        {r.error ? <div className="p-4"><ErrorPanel error={r.error} /></div> : !r.data.items.length ? (
          <EmptyState title="কোনো এলাকা পাওয়া যায়নি" hint="ফিল্টার বদলে আবার চেষ্টা করুন।" />
        ) : (
          <>
            <TableWrap>
              <table className="table">
                <thead><tr><th scope="col">নাম</th><th scope="col">স্তর</th><th scope="col">পাথ</th><th scope="col">প্রমাণ</th><th scope="col">প্রকাশ</th><th scope="col">উৎস</th><th scope="col">শেষ পর্যালোচনা</th></tr></thead>
                <tbody>
                  {r.data.items.map((a) => (
                    <tr key={a.id}>
                      <td><Link href={`/areas/${a.id}`} className="font-medium text-secondary hover:underline">{a.name_bn}</Link><div className="font-en text-xs text-muted">{a.name_en}</div></td>
                      <td className="whitespace-nowrap">{LEVEL_LABEL[a.level]?.bn ?? a.level}</td>
                      <td className="font-en text-xs">{a.path}</td>
                      <td><EvidenceBadge level={a.evidence_level} /></td>
                      <td><PublicBadge eligible={a.production_eligible} /></td>
                      <td className="font-en text-xs">{a.evidence_source_key ?? <span className="text-muted">—</span>}</td>
                      <td className="whitespace-nowrap text-xs">{a.last_reviewed_at ? formatDateTime(a.last_reviewed_at) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
            <Pager basePath="/areas" params={sp} nextCursor={r.data.next_cursor} hasCursor={!!sp.cursor} />
          </>
        )}
      </Card>
    </>
  );
}
