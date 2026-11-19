import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { DataSource } from '@elaka360/shared';
import { LEVEL_LABEL, formatNumber } from '@elaka360/shared';
import { updateArea, verifyRecord } from '../../actions';
import { AreaEditForm } from '@/components/AreaEditForm';
import { AuditTable } from '@/components/Audit';
import { VerifyForm } from '@/components/VerifyForm';
import { Card, ErrorPanel, EvidenceBadge, KV, PageHeader, PublicBadge, StatusChip, formatDateTime } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import type { AdminAreaDetail } from '@/lib/types';

export const metadata = { title: 'এলাকার বিস্তারিত' };

const SITE = process.env.PUBLIC_SITE_URL ?? 'http://localhost:3000';

export default async function AreaDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { ok, can } = await access('areas.read');
  if (!ok) return <Forbidden perm="areas.read" />;
  const { id: raw } = await params;
  const id = Number(raw);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  const [r, src] = await Promise.all([
    apiTry<AdminAreaDetail>(`/v1/admin/areas/${id}`),
    can('areas.verify') ? apiTry<{ items: DataSource[] }>('/v1/admin/sources') : Promise.resolve(null),
  ]);
  if (r.error?.status === 404) notFound();
  if (r.error) return <><PageHeader title="এলাকা" back={{ href: '/areas', label: 'এলাকার তালিকা' }} /><ErrorPanel error={r.error} /></>;
  const a = r.data;

  return (
    <>
      <PageHeader title={a.name_bn} en={`${a.name_en} · ${LEVEL_LABEL[a.level]?.en ?? a.level}`} back={{ href: '/areas', label: 'এলাকার তালিকা' }}>
        <EvidenceBadge level={a.evidence_level} />
        <PublicBadge eligible={a.production_eligible} />
        {a.production_eligible && <a className="btn btn-outline btn-sm" href={`${SITE}/${a.path}`} target="_blank" rel="noopener noreferrer">সাইটে দেখুন ↗</a>}
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1fr_24rem]">
        <div className="space-y-4">
          <Card title="বর্তমান তথ্য" en="Current record">
            <div className="p-4">
              <KV items={[
                ['আইডি', <span key="id" className="font-en">#{a.id}</span>],
                ['স্তর', LEVEL_LABEL[a.level]?.bn ?? a.level],
                ['পাথ', <span key="p" className="font-en">{a.path}</span>],
                ['অভিভাবক', a.parent_id ? <Link key="par" className="font-en text-secondary hover:underline" href={`/areas/${a.parent_id}`}>#{a.parent_id}</Link> : null],
                ['বিবিএস কোড', a.bbs_code && <span key="b" className="font-en">{a.bbs_code}</span>],
                ['ওয়েবসাইট', a.website && <a key="w" className="font-en break-all text-secondary hover:underline" href={a.website} target="_blank" rel="noopener noreferrer nofollow">{a.website}</a>],
                ['স্থানাঙ্ক', a.lat != null && a.lon != null ? <span key="c" className="font-en">{a.lat}, {a.lon}</span> : null],
                ['অবস্থা', <StatusChip key="s" status={a.status} />],
                ['প্রমাণের উৎস', a.evidence_source_key && <span key="es" className="font-en">{a.evidence_source_key}</span>],
                ['ডেটা উৎস', a.data_source_key && <span key="ds" className="font-en">{a.data_source_key}</span>],
                ['যাচাইয়ের নোট', a.verification_notes],
                ['নোট', a.notes],
                ['শেষ পর্যালোচনা', a.last_reviewed_at ? formatDateTime(a.last_reviewed_at) : null],
              ]} />
            </div>
          </Card>

          <Card title="অধীন এলাকা" en="Children">
            {a.children.length ? (
              <ul className="divide-y divide-line">
                {a.children.map((c) => (
                  <li key={c.level} className="flex items-center justify-between px-4 py-2 text-sm">
                    <Link className="text-secondary hover:underline" href={`/areas?parent_id=${a.id}&level=${c.level}`}>{LEVEL_LABEL[c.level]?.plural_bn ?? c.level}</Link>
                    <span>{formatNumber(c.n)}টি · প্রকাশিত {formatNumber(c.public)}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="p-4 text-sm text-muted">কোনো অধীন এলাকা নেই।</p>}
          </Card>

          {can('areas.edit') && (
            <Card title="সম্পাদনা" en="Edit">
              <div className="p-4"><AreaEditForm action={updateArea.bind(null, a.id)} area={a} /></div>
            </Card>
          )}

          <Card title="পরিবর্তনের ইতিহাস" en="Change history">
            <AuditTable items={a.history} showEntity={false} />
          </Card>
        </div>

        {can('areas.verify') && (
          <div>
            <Card title="যাচাই ও প্রকাশ" en="Verify" className="xl:sticky xl:top-20">
              <div className="p-4">
                {src?.error ? <ErrorPanel error={src.error} title="উৎসের তালিকা আনা যায়নি" /> : (
                  <VerifyForm action={verifyRecord.bind(null, 'areas', a.id)} sources={src?.data?.items ?? []}
                    current={{ evidence_level: a.evidence_level, evidence_source_id: a.evidence_source_id, production_eligible: a.production_eligible, verification_notes: a.verification_notes }} />
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
