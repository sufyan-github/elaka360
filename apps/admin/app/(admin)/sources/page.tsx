import type { DataSource } from '@elaka360/shared';
import { formatNumber, toBnDigits } from '@elaka360/shared';
import { createSource, updateSource } from '../actions';
import { SourceForm } from '@/components/SourceForm';
import { Card, Chip, EmptyState, ErrorPanel, PageHeader, TableWrap, formatDateTime } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';

export const metadata = { title: 'উৎস' };

export default async function SourcesPage() {
  const { ok, can } = await access('sources.read');
  if (!ok) return <Forbidden perm="sources.read" />;
  const r = await apiTry<{ items: DataSource[] }>('/v1/admin/sources');
  const edit = can('sources.edit');
  return (
    <>
      <PageHeader title="উৎস" en="Data sources">{r.data && <span className="text-sm text-muted">{formatNumber(r.data.items.length)}টি</span>}</PageHeader>
      {edit && (
        <details className="mb-4 rounded-card border border-line bg-surface shadow-card">
          <summary className="cursor-pointer px-4 py-3 font-semibold">+ নতুন উৎস <span className="font-en text-xs font-normal text-muted">· Register a source</span></summary>
          <div className="border-t border-line p-4"><SourceForm action={createSource} /></div>
        </details>
      )}
      <Card>
        {r.error ? <div className="p-4"><ErrorPanel error={r.error} /></div> : !r.data.items.length ? <EmptyState title="কোনো উৎস নিবন্ধিত নেই" /> : (
          <TableWrap>
            <table className="table">
              <thead><tr><th scope="col">কী ও নাম</th><th scope="col">ধরন</th><th scope="col">আস্থা</th><th scope="col">লাইসেন্স</th><th scope="col">ব্যবহার</th><th scope="col">অবস্থা</th>{edit && <th scope="col"><span className="sr-only">সম্পাদনা</span></th>}</tr></thead>
              <tbody>
                {r.data.items.map((s) => (
                  <tr key={s.id}>
                    <td className="min-w-[16rem]">
                      <div className="font-en text-xs font-semibold">{s.key}</div>
                      <div>{s.name}</div>
                      {s.url ? <a className="font-en break-all text-xs text-secondary hover:underline" href={s.url} target="_blank" rel="noopener noreferrer nofollow">{s.url}</a> : <span className="text-xs text-danger">URL নেই — প্রকাশের উৎস হতে পারে না</span>}
                      {(s.access_date || s.publication_date) && <div className="text-xs text-muted">{s.publication_date && `প্রকাশ ${formatDateTime(s.publication_date)}`}{s.access_date && ` · দেখা ${formatDateTime(s.access_date)}`}</div>}
                    </td>
                    <td className="font-en text-xs">{s.source_type}</td>
                    <td><Chip tone={s.trust_level >= 4 ? 'tint' : 'line'}>{toBnDigits(s.trust_level)}/৫</Chip></td>
                    <td className="font-en text-xs">{s.license ?? '—'}</td>
                    <td className="tabular-nums">{formatNumber(s.usage_count ?? 0)}</td>
                    <td>{s.active ? <Chip tone="tint">সক্রিয়</Chip> : <Chip tone="danger">নিষ্ক্রিয়</Chip>}</td>
                    {edit && (
                      <td className="min-w-[8rem]">
                        <details>
                          <summary className="btn btn-outline btn-sm cursor-pointer list-none">সম্পাদনা</summary>
                          <div className="mt-3 w-[min(36rem,80vw)]"><SourceForm action={updateSource.bind(null, s.id)} source={s} /></div>
                        </details>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>
    </>
  );
}
