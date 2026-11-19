import { notFound } from 'next/navigation';
import type { DataSource } from '@elaka360/shared';
import { OWNERSHIP_LABEL } from '@/lib/labels';
import { updatePlace, verifyRecord } from '../../actions';
import { AuditTable } from '@/components/Audit';
import { PlaceForm } from '@/components/PlaceForm';
import { VerifyForm } from '@/components/VerifyForm';
import { Card, ErrorPanel, EvidenceBadge, KV, PageHeader, PublicBadge, StatusChip, formatDateTime } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { categoryOptions } from '@/lib/categories';
import { Forbidden, access } from '@/lib/guard';
import type { AdminPlaceDetail } from '@/lib/types';

export const metadata = { title: 'স্থানের বিস্তারিত' };

const SITE = process.env.PUBLIC_SITE_URL ?? 'http://localhost:3000';

export default async function PlaceDetailPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ created?: string }> }) {
  const { ok, can } = await access('places.read');
  if (!ok) return <Forbidden perm="places.read" />;
  const { id: raw } = await params;
  const { created } = await searchParams;
  const id = Number(raw);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  const [r, src, cats] = await Promise.all([
    apiTry<AdminPlaceDetail>(`/v1/admin/places/${id}`),
    can('places.verify') ? apiTry<{ items: DataSource[] }>('/v1/admin/sources') : Promise.resolve(null),
    categoryOptions(),
  ]);
  if (r.error?.status === 404) notFound();
  if (r.error) return <><PageHeader title="স্থান" back={{ href: '/places', label: 'স্থানের তালিকা' }} /><ErrorPanel error={r.error} /></>;
  const p = r.data;
  const osm = p.lat != null && p.lon != null ? `https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lon}#map=17/${p.lat}/${p.lon}` : null;

  return (
    <>
      <PageHeader title={p.name_bn} en={`${p.name_en ?? ''} · ${p.public_id}`} back={{ href: '/places', label: 'স্থানের তালিকা' }}>
        <EvidenceBadge level={p.evidence_level} />
        <PublicBadge eligible={p.production_eligible} />
        {p.production_eligible && <a className="btn btn-outline btn-sm" href={`${SITE}/p/${p.slug}`} target="_blank" rel="noopener noreferrer">সাইটে দেখুন ↗</a>}
      </PageHeader>
      {created && <p role="status" className="mb-4 rounded-chip bg-tint px-3 py-2 text-sm text-primary">স্থান তৈরি হয়েছে (অযাচাইকৃত, অপ্রকাশিত)। প্রকাশের আগে যাচাই করুন।</p>}

      <div className="grid gap-4 xl:grid-cols-[1fr_24rem]">
        <div className="space-y-4">
          <Card title="বর্তমান তথ্য" en="Current record">
            <div className="p-4">
              <KV items={[
                ['আইডি', <span key="i" className="font-en">#{p.id} · {p.public_id} · /p/{p.slug}</span>],
                ['ক্যাটাগরি', cats.label(p.subcategory_key ?? p.category_key)],
                ['এলাকা', p.area_path && <span key="a" className="font-en">{p.area_path}</span>],
                ['মালিকানা', p.ownership ? OWNERSHIP_LABEL[p.ownership] ?? p.ownership : null],
                ['ঠিকানা', [p.address_bn, p.address_en].filter(Boolean).join(' · ')],
                ['স্থানাঙ্ক', osm ? <span key="c" className="font-en">{p.lat}, {p.lon} · <a className="text-secondary hover:underline" href={osm} target="_blank" rel="noopener noreferrer nofollow">OpenStreetMap ↗</a></span> : null],
                ['ফোন', p.phones?.length ? <span key="ph" className="font-en">{p.phones.join(', ')}</span> : null],
                ['ইমেইল', p.email && <span key="e" className="font-en">{p.email}</span>],
                ['ওয়েবসাইট', p.website && <a key="w" className="font-en break-all text-secondary hover:underline" href={p.website} target="_blank" rel="noopener noreferrer nofollow">{p.website}</a>],
                ['অবস্থা', <StatusChip key="s" status={p.status} />],
                ['যাচাই অবস্থা', <span key="vs" className="font-en">{p.verification_status}</span>],
                ['প্রমাণের উৎস', p.evidence_source_key && <span key="es" className="font-en">{p.evidence_source_key}</span>],
                ['যাচাইয়ের নোট', p.verification_notes],
                ['উৎস-নোট', p.source_notes],
                ['হালনাগাদ', formatDateTime(p.updated_at)],
              ]} />
            </div>
          </Card>
          {can('places.edit') && (
            <Card title="সম্পাদনা" en="Edit">
              <div className="p-4"><PlaceForm action={updatePlace.bind(null, p.id)} categories={cats.options} place={p} /></div>
            </Card>
          )}
          <Card title="পরিবর্তনের ইতিহাস" en="Change history"><AuditTable items={p.history} showEntity={false} /></Card>
        </div>
        {can('places.verify') && (
          <div>
            <Card title="যাচাই ও প্রকাশ" en="Verify" className="xl:sticky xl:top-20">
              <div className="p-4">
                {src?.error ? <ErrorPanel error={src.error} title="উৎসের তালিকা আনা যায়নি" /> : (
                  <VerifyForm action={verifyRecord.bind(null, 'places', p.id)} sources={src?.data?.items ?? []}
                    current={{ evidence_level: p.evidence_level, evidence_source_id: p.evidence_source_id, production_eligible: p.production_eligible, verification_notes: p.verification_notes }} />
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
