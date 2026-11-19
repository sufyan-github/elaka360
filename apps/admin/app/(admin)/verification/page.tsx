import Link from 'next/link';
import type { DataSource } from '@elaka360/shared';
import { LEVEL_LABEL, formatNumber } from '@elaka360/shared';
import { verifyRecord } from '../actions';
import { AREA_LEVELS, EvidenceSelect } from '@/components/filters';
import { VerifyForm } from '@/components/VerifyForm';
import { Card, EmptyState, ErrorPanel, EvidenceBadge, KV, PageHeader, Pager, PublicBadge, formatDateTime } from '@/components/ui';
import { apiTry, qs } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import type { AdminAreaDetail, AdminAreaRow, AdminPlaceDetail, AdminPlaceRow, Page } from '@/lib/types';

export const metadata = { title: 'যাচাই কেন্দ্র' };

type SP = { kind?: string; level?: string; evidence?: string; q?: string; cursor?: string; id?: string };

export default async function VerificationPage({ searchParams }: { searchParams: Promise<SP> }) {
  const { ok, can } = await access('verify');
  if (!ok) return <Forbidden perm="areas.verify / places.verify" />;
  const sp = await searchParams;
  const kind: 'places' | 'areas' = sp.kind === 'areas' || (!can('places.verify') && sp.kind !== 'places') ? 'areas' : 'places';
  const allowed = can(`${kind}.verify`);
  const level = kind === 'areas' ? sp.level || 'upazila' : undefined;
  const listPath = kind === 'places'
    ? `/v1/admin/places${qs({ eligible: 'false', status: 'active', evidence: sp.evidence, q: sp.q, cursor: sp.cursor, limit: 25 })}`
    : `/v1/admin/areas${qs({ eligible: 'false', level, evidence: sp.evidence, q: sp.q, cursor: sp.cursor, limit: 25 })}`;
  const selected = sp.id && /^\d+$/.test(sp.id) ? Number(sp.id) : null;

  const [list, rec, src] = await Promise.all([
    allowed ? apiTry<Page<AdminAreaRow | AdminPlaceRow>>(listPath) : Promise.resolve(null),
    allowed && selected ? apiTry<AdminAreaDetail | AdminPlaceDetail>(`/v1/admin/${kind}/${selected}`) : Promise.resolve(null),
    allowed && selected ? apiTry<{ items: DataSource[] }>('/v1/admin/sources') : Promise.resolve(null),
  ]);

  const keep = { kind, level, evidence: sp.evidence, q: sp.q, cursor: sp.cursor };
  const hrefWith = (o: Record<string, string | undefined>) => `/verification${qs({ ...keep, ...o })}`;

  return (
    <>
      <PageHeader title="যাচাই কেন্দ্র" en="Verification centre" />
      <p className="mb-4 text-sm text-muted">
        যেসব রেকর্ড এখনো প্রকাশিত নয় (production_eligible = false)। একটি বেছে নিন, বর্তমান তথ্য ও উৎস মিলিয়ে দেখুন, তারপর যাচাইয়ের সিদ্ধান্ত দিন।
        শুধু সরকারি বা দ্বিতীয় উৎসের, URL-সহ নামযুক্ত উৎসের তথ্য প্রকাশ করা যায়।
      </p>

      <div role="tablist" aria-label="রেকর্ডের ধরন" className="mb-4 flex gap-2">
        {can('places.verify') && <Link role="tab" aria-selected={kind === 'places'} href="/verification?kind=places" className={`btn ${kind === 'places' ? 'btn-primary' : 'btn-outline'}`}>স্থান · Places</Link>}
        {can('areas.verify') && <Link role="tab" aria-selected={kind === 'areas'} href="/verification?kind=areas" className={`btn ${kind === 'areas' ? 'btn-primary' : 'btn-outline'}`}>এলাকা · Areas</Link>}
      </div>

      {!allowed ? <Forbidden perm={`${kind}.verify`} /> : (
        <div className="grid gap-4 lg:grid-cols-[minmax(18rem,26rem)_1fr]">
          <Card title="কাজের তালিকা" en={list?.data ? `${formatNumber(list.data.total)} pending` : 'Queue'}>
            <form action="/verification" method="get" className="flex flex-wrap items-end gap-2 border-b border-line p-3" role="search">
              <input type="hidden" name="kind" value={kind} />
              {kind === 'areas' && (
                <div className="min-w-[8rem] flex-1">
                  <label htmlFor="v-level" className="mb-1 block text-xs text-muted">স্তর</label>
                  <select id="v-level" name="level" defaultValue={level} className="input">
                    {AREA_LEVELS.map((l) => <option key={l} value={l}>{LEVEL_LABEL[l].bn}</option>)}
                  </select>
                </div>
              )}
              <div className="min-w-[8rem] flex-1">
                <label htmlFor="v-evidence" className="mb-1 block text-xs text-muted">প্রমাণ</label>
                <EvidenceSelect id="v-evidence" value={sp.evidence} />
              </div>
              <div className="min-w-[8rem] flex-1">
                <label htmlFor="v-q" className="mb-1 block text-xs text-muted">খুঁজুন</label>
                <input id="v-q" name="q" type="search" defaultValue={sp.q} className="input" />
              </div>
              <button type="submit" className="btn btn-outline">ফিল্টার</button>
            </form>
            {list?.error ? <div className="p-3"><ErrorPanel error={list.error} /></div> : !list?.data?.items.length ? (
              <EmptyState title="সারি খালি" hint="এই ফিল্টারে কোনো অপ্রকাশিত রেকর্ড নেই।" />
            ) : (
              <>
                <ul className="max-h-[65vh] divide-y divide-line overflow-y-auto">
                  {list.data.items.map((it) => {
                    const on = it.id === selected;
                    const sub = 'public_id' in it ? `${it.public_id} · ${it.area_path ?? '—'}` : it.path;
                    return (
                      <li key={it.id}>
                        <Link href={hrefWith({ id: String(it.id) })} aria-current={on ? 'true' : undefined}
                          className={`block px-3 py-2 ${on ? 'bg-tint' : 'hover:bg-tint'}`}>
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium">{it.name_bn}</span>
                            <EvidenceBadge level={it.evidence_level} />
                          </div>
                          <div className="font-en truncate text-xs text-muted">{sub}</div>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
                <Pager basePath="/verification" params={{ kind, level, evidence: sp.evidence, q: sp.q }} nextCursor={list.data.next_cursor} hasCursor={!!sp.cursor} />
              </>
            )}
          </Card>

          <div>
            {!selected ? (
              <Card><EmptyState title="একটি রেকর্ড বেছে নিন" hint="বাঁ দিকের তালিকা থেকে একটি রেকর্ড খুলুন; বর্তমান তথ্য ও যাচাই ফর্ম পাশাপাশি দেখাবে।" /></Card>
            ) : rec?.error ? <ErrorPanel error={rec.error} /> : rec?.data ? (
              <div className="grid gap-4 2xl:grid-cols-2">
                <Card title={rec.data.name_bn} en="Current values"
                  action={<Link className="text-sm text-secondary hover:underline" href={`/${kind}/${rec.data.id}`}>পূর্ণ পাতা →</Link>}>
                  <div className="space-y-3 p-4">
                    <div className="flex flex-wrap gap-2"><EvidenceBadge level={rec.data.evidence_level} /><PublicBadge eligible={rec.data.production_eligible} /></div>
                    <RecordFacts rec={rec.data} />
                  </div>
                </Card>
                <Card title="যাচাইয়ের সিদ্ধান্ত" en="Verify">
                  <div className="p-4">
                    {src?.error ? <ErrorPanel error={src.error} title="উৎসের তালিকা আনা যায়নি" /> : (
                      <VerifyForm key={`${kind}-${rec.data.id}`} idPrefix={`vc-${rec.data.id}`} action={verifyRecord.bind(null, kind, rec.data.id)} sources={src?.data?.items ?? []}
                        current={{ evidence_level: rec.data.evidence_level, evidence_source_id: rec.data.evidence_source_id, production_eligible: rec.data.production_eligible, verification_notes: rec.data.verification_notes }} />
                    )}
                  </div>
                </Card>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </>
  );
}

function RecordFacts({ rec }: { rec: AdminAreaDetail | AdminPlaceDetail }) {
  const last = rec.history[0];
  if ('public_id' in rec) {
    const osm = rec.lat != null && rec.lon != null ? `https://www.openstreetmap.org/?mlat=${rec.lat}&mlon=${rec.lon}#map=17/${rec.lat}/${rec.lon}` : null;
    return (
      <KV items={[
        ['নাম', <span key="n">{rec.name_bn}{rec.name_en && <span className="font-en text-muted"> · {rec.name_en}</span>}</span>],
        ['পাবলিক আইডি', <span key="p" className="font-en">{rec.public_id}</span>],
        ['ক্যাটাগরি', <span key="c" className="font-en">{rec.subcategory_key ?? rec.category_key}</span>],
        ['এলাকা', rec.area_path && <span key="a" className="font-en">{rec.area_path}</span>],
        ['ঠিকানা', [rec.address_bn, rec.address_en].filter(Boolean).join(' · ')],
        ['স্থানাঙ্ক', osm ? <span key="o" className="font-en">{rec.lat}, {rec.lon} · <a className="text-secondary hover:underline" href={osm} target="_blank" rel="noopener noreferrer nofollow">OSM ↗</a></span> : null],
        ['ফোন', rec.phones?.length ? <span key="ph" className="font-en">{rec.phones.join(', ')}</span> : null],
        ['ওয়েবসাইট', rec.website && <a key="w" className="font-en break-all text-secondary hover:underline" href={rec.website} target="_blank" rel="noopener noreferrer nofollow">{rec.website}</a>],
        ['বর্তমান উৎস', rec.evidence_source_key && <span key="s" className="font-en">{rec.evidence_source_key}</span>],
        ['উৎস-নোট', rec.source_notes],
        ['যাচাইয়ের নোট', rec.verification_notes],
        ['শেষ পরিবর্তন', last ? `${formatDateTime(last.at)} · ${last.action}` : null],
      ]} />
    );
  }
  return (
    <KV items={[
      ['নাম', <span key="n">{rec.name_bn} <span className="font-en text-muted">· {rec.name_en}</span></span>],
      ['স্তর', LEVEL_LABEL[rec.level]?.bn ?? rec.level],
      ['পাথ', <span key="p" className="font-en">{rec.path}</span>],
      ['বিবিএস কোড', rec.bbs_code && <span key="b" className="font-en">{rec.bbs_code}</span>],
      ['ওয়েবসাইট', rec.website && <a key="w" className="font-en break-all text-secondary hover:underline" href={rec.website} target="_blank" rel="noopener noreferrer nofollow">{rec.website}</a>],
      ['বর্তমান উৎস', rec.evidence_source_key && <span key="s" className="font-en">{rec.evidence_source_key}</span>],
      ['ডেটা উৎস', rec.data_source_key && <span key="d" className="font-en">{rec.data_source_key}</span>],
      ['যাচাইয়ের নোট', rec.verification_notes],
      ['নোট', rec.notes],
      ['শেষ পরিবর্তন', last ? `${formatDateTime(last.at)} · ${last.action}` : null],
    ]} />
  );
}
