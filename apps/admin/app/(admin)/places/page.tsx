import Link from 'next/link';
import { formatNumber } from '@elaka360/shared';
import { EligibleSelect, EvidenceSelect } from '@/components/filters';
import { Card, EmptyState, ErrorPanel, EvidenceBadge, FilterBar, FilterField, PageHeader, Pager, PublicBadge, StatusChip, TableWrap, formatDateTime } from '@/components/ui';
import { apiTry, qs } from '@/lib/api';
import { categoryOptions } from '@/lib/categories';
import { Forbidden, access } from '@/lib/guard';
import { PLACE_STATUSES, STATUS_LABEL } from '@/lib/labels';
import type { AdminPlaceRow, Page } from '@/lib/types';

export const metadata = { title: 'স্থান' };

type SP = { q?: string; category?: string; evidence?: string; eligible?: string; status?: string; cursor?: string };

export default async function PlacesPage({ searchParams }: { searchParams: Promise<SP> }) {
  const { ok, can } = await access('places.read');
  if (!ok) return <Forbidden perm="places.read" />;
  const sp = await searchParams;
  const [r, cats] = await Promise.all([
    apiTry<Page<AdminPlaceRow>>(`/v1/admin/places${qs({ q: sp.q, category: sp.category, evidence: sp.evidence, eligible: sp.eligible, status: sp.status, cursor: sp.cursor, limit: 50 })}`),
    categoryOptions(),
  ]);
  return (
    <>
      <PageHeader title="স্থান" en="Places">
        {r.data && <span className="text-sm text-muted">মোট {formatNumber(r.data.total)}টি</span>}
        {can('places.edit') && <Link href="/places/new" className="btn btn-primary">+ নতুন স্থান</Link>}
      </PageHeader>
      <FilterBar action="/places" resetHref="/places">
        <FilterField label="খুঁজুন (নাম বা পাবলিক আইডি)" htmlFor="q" wide><input id="q" name="q" type="search" defaultValue={sp.q} className="input" /></FilterField>
        <FilterField label="ক্যাটাগরি" htmlFor="category">
          <select id="category" name="category" defaultValue={sp.category ?? ''} className="input">
            <option value="">সব ক্যাটাগরি</option>
            {cats.options.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
        </FilterField>
        <FilterField label="প্রমাণ" htmlFor="evidence"><EvidenceSelect value={sp.evidence} /></FilterField>
        <FilterField label="প্রকাশ" htmlFor="eligible"><EligibleSelect value={sp.eligible} /></FilterField>
        <FilterField label="অবস্থা" htmlFor="status">
          <select id="status" name="status" defaultValue={sp.status ?? ''} className="input">
            <option value="">সব</option>
            {PLACE_STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </FilterField>
      </FilterBar>
      <Card>
        {r.error ? <div className="p-4"><ErrorPanel error={r.error} /></div> : !r.data.items.length ? (
          <EmptyState title="কোনো স্থান পাওয়া যায়নি" hint={can('places.edit') ? 'ফিল্টার বদলান অথবা নতুন স্থান যোগ করুন।' : 'ফিল্টার বদলে আবার চেষ্টা করুন।'} />
        ) : (
          <>
            <TableWrap>
              <table className="table">
                <thead><tr><th scope="col">নাম</th><th scope="col">ক্যাটাগরি</th><th scope="col">এলাকা</th><th scope="col">প্রমাণ</th><th scope="col">প্রকাশ</th><th scope="col">অবস্থা</th><th scope="col">হালনাগাদ</th></tr></thead>
                <tbody>
                  {r.data.items.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <Link href={`/places/${p.id}`} className="font-medium text-secondary hover:underline">{p.name_bn}</Link>
                        <div className="font-en text-xs text-muted">{p.public_id}{p.name_en ? ` · ${p.name_en}` : ''}</div>
                      </td>
                      <td className="text-sm">{cats.label(p.subcategory_key ?? p.category_key)}</td>
                      <td className="font-en text-xs">{p.area_path ?? '—'}</td>
                      <td><EvidenceBadge level={p.evidence_level} /></td>
                      <td><PublicBadge eligible={p.production_eligible} /></td>
                      <td><StatusChip status={p.status} /></td>
                      <td className="whitespace-nowrap text-xs">{formatDateTime(p.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
            <Pager basePath="/places" params={sp} nextCursor={r.data.next_cursor} hasCursor={!!sp.cursor} />
          </>
        )}
      </Card>
    </>
  );
}
