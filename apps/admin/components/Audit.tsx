import Link from 'next/link';
import type { AuditEntry } from '@elaka360/shared';
import { EmptyState, TableWrap, formatDateTime } from './ui';

const ENTITY_LABEL: Record<string, string> = {
  admin_area: 'এলাকা', place: 'স্থান', contribution: 'অবদান', data_source: 'উৎস', user: 'ব্যবহারকারী', review: 'রিভিউ',
};

export function entityHref(entity: string, id: string): string | null {
  switch (entity) {
    case 'admin_area': return `/areas/${id}`;
    case 'place': return `/places/${id}`;
    case 'contribution': return `/moderation/${id}`;
    case 'data_source': return '/sources';
    default: return null;
  }
}

function show(v: unknown): string {
  if (v === undefined) return '∅';
  if (v === null) return 'null';
  if (typeof v === 'string') return v;
  return JSON.stringify(v);
}

/** Field-by-field diff of an audit entry's before/after snapshots. */
export function FieldDiff({ before, after }: { before: unknown; after: unknown }) {
  const obj = (x: unknown) => (x && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : null);
  const b = obj(before);
  const a = obj(after);
  if (!b && !a) {
    if (before === null && after === null) return <p className="text-xs text-muted">কোনো স্ন্যাপশট নেই · no snapshot recorded</p>;
    return <pre className="font-en overflow-x-auto text-xs">{show(before)} → {show(after)}</pre>;
  }
  const keys = [...new Set([...Object.keys(b ?? {}), ...Object.keys(a ?? {})])];
  const rows = keys.filter((k) => JSON.stringify(b?.[k]) !== JSON.stringify(a?.[k]));
  if (!rows.length) return <p className="text-xs text-muted">মান অপরিবর্তিত · no field changed</p>;
  return (
    <table className="font-en w-full text-xs">
      <thead>
        <tr className="text-left text-muted"><th className="py-1 pr-3 font-medium">field</th><th className="py-1 pr-3 font-medium">before</th><th className="py-1 font-medium">after</th></tr>
      </thead>
      <tbody>
        {rows.map((k) => (
          <tr key={k} className="border-t border-line align-top">
            <td className="py-1 pr-3 font-medium">{k}</td>
            <td className="max-w-xs break-words py-1 pr-3"><del className="bg-danger-tint text-danger decoration-1">{b ? show(b[k]) : '∅'}</del></td>
            <td className="max-w-xs break-words py-1"><ins className="bg-tint text-primary no-underline">{a ? show(a[k]) : '∅'}</ins></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function AuditTable({ items, showEntity = true, empty = 'কোনো পরিবর্তনের রেকর্ড নেই' }: { items: AuditEntry[]; showEntity?: boolean; empty?: string }) {
  if (!items.length) return <EmptyState title={empty} />;
  return (
    <TableWrap>
      <table className="table">
        <thead>
          <tr>
            <th scope="col">সময়</th>
            <th scope="col">কে</th>
            <th scope="col">কাজ</th>
            {showEntity && <th scope="col">রেকর্ড</th>}
            <th scope="col">কারণ ও পরিবর্তন</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e) => {
            const href = entityHref(e.entity, e.entity_id);
            return (
              <tr key={e.id}>
                <td className="whitespace-nowrap text-xs">{formatDateTime(e.at)}</td>
                <td className="text-sm">{e.actor_name ?? <span className="text-muted">সিস্টেম</span>}{e.actor_id && <span className="font-en ml-1 text-xs text-muted">#{e.actor_id}</span>}</td>
                <td><code className="font-en text-xs">{e.action}</code></td>
                {showEntity && (
                  <td className="whitespace-nowrap text-sm">
                    {ENTITY_LABEL[e.entity] ?? e.entity}{' '}
                    {href ? <Link className="font-en text-secondary hover:underline" href={href}>#{e.entity_id}</Link> : <span className="font-en">#{e.entity_id}</span>}
                  </td>
                )}
                <td className="min-w-[16rem]">
                  {e.reason && <p className="mb-1 text-sm">{e.reason}</p>}
                  <details>
                    <summary className="cursor-pointer text-xs text-secondary">পরিবর্তন দেখুন · diff</summary>
                    <div className="mt-2"><FieldDiff before={e.before} after={e.after} /></div>
                  </details>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </TableWrap>
  );
}
