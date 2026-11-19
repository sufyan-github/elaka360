import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Contribution, Place } from '@elaka360/shared';
import { CONTRIBUTION_STATUS_LABEL } from '@elaka360/shared';
import { decideContribution } from '../../actions';
import { DecisionForm } from '@/components/DecisionForm';
import { Card, Chip, EmptyState, ErrorPanel, KV, PageHeader, formatDateTime } from '@/components/ui';
import { apiTry, publicGet } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import { CONTRIBUTION_TYPE_LABEL, NEW_PLACE_TYPES } from '@/lib/labels';

export const metadata = { title: 'অবদান' };

const show = (v: unknown) => (v === null || v === undefined || v === '' || (Array.isArray(v) && !v.length) ? '—' : Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v));

const FIELD_LABEL: Record<string, string> = {
  name_bn: 'বাংলা নাম', name_en: 'ইংরেজি নাম', category_key: 'ক্যাটাগরি', ownership: 'মালিকানা', address: 'ঠিকানা', description: 'বিবরণ',
  website: 'ওয়েবসাইট', phones: 'ফোন', field: 'ঘর', current_value: 'বর্তমান মান (জমাদাতার মতে)', proposed_value: 'প্রস্তাবিত মান', note: 'নোট', caption: 'ক্যাপশন',
};

/** Place fields a correction's `field` may refer to, mapped to the public place shape. */
const PLACE_FIELD: Record<string, (p: Place) => unknown> = {
  name_bn: (p) => p.name_bn, name_en: (p) => p.name_en, address: (p) => p.address_bn, address_bn: (p) => p.address_bn, address_en: (p) => p.address_en,
  phones: (p) => p.phones, phone: (p) => p.phones, website: (p) => p.website, email: (p) => p.email, description: (p) => p.description_bn,
  description_bn: (p) => p.description_bn, ownership: (p) => p.ownership, postcode: (p) => p.postcode, established: (p) => p.established,
  opening_hours: (p) => p.opening_hours, category: (p) => p.subcategory_key ?? p.category_key, category_key: (p) => p.subcategory_key ?? p.category_key,
  location: (p) => (p.lat != null ? `${p.lat}, ${p.lon}` : null),
};

export default async function ContributionPage({ params }: { params: Promise<{ id: string }> }) {
  const { ok } = await access('contributions.moderate');
  if (!ok) return <Forbidden perm="contributions.moderate" />;
  const { id: raw } = await params;
  const id = Number(raw);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  const r = await apiTry<Contribution>(`/v1/admin/contributions/${id}`);
  if (r.error?.status === 404) notFound();
  if (r.error) return <><PageHeader title={`অবদান #${id}`} back={{ href: '/moderation', label: 'মডারেশন সারি' }} /><ErrorPanel error={r.error} /></>;
  const c = r.data;

  // The admin contribution detail only carries the target's slug; the public place read works when it is published.
  let target: Place | null = null;
  let targetNote: string | null = null;
  if (c.target_place_slug) {
    try {
      target = await publicGet<Place>(`/v1/places/${encodeURIComponent(c.target_place_slug)}`, 0);
    } catch {
      targetNote = 'লক্ষ্য স্থানটি প্রকাশিত নয় বা পাওয়া যায়নি; স্থানের তালিকায় নাম দিয়ে খুঁজুন।';
    }
  }
  const osm = c.lat != null && c.lon != null ? `https://www.openstreetmap.org/?mlat=${c.lat}&mlon=${c.lon}#map=17/${c.lat}/${c.lon}` : null;
  const payloadKeys = Object.keys(c.payload ?? {});
  const corrField = typeof c.payload.field === 'string' ? c.payload.field : null;

  return (
    <>
      <PageHeader title={`অবদান #${c.id}`} en={`${CONTRIBUTION_TYPE_LABEL[c.type]?.en ?? c.type}`} back={{ href: '/moderation', label: 'মডারেশন সারি' }}>
        <Chip>{CONTRIBUTION_TYPE_LABEL[c.type]?.bn ?? c.type}</Chip>
        <Chip tone={c.status === 'rejected' ? 'danger' : c.status === 'approved' ? 'tint' : 'line'}>{CONTRIBUTION_STATUS_LABEL[c.status]?.bn ?? c.status}</Chip>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1fr_26rem]">
        <div className="space-y-4">
          <p className="rounded-chip border border-dashed border-line bg-surface px-3 py-2 text-sm text-muted">
            এটি ব্যবহারকারীর জমা দেওয়া কমিউনিটি তথ্য — যাচাইকৃত নয়। অনুমোদন মানে প্রকাশ নয়; প্রকাশের জন্য আলাদা যাচাই লাগবে।
          </p>
          <Card title="জমা দেওয়া তথ্য" en="Submitted payload">
            {payloadKeys.length ? (
              <div className="overflow-x-auto">
                <table className="table">
                  <thead>
                    <tr><th scope="col">ঘর</th><th scope="col">জমা দেওয়া মান</th>{target && !corrField && <th scope="col">বর্তমান রেকর্ডে</th>}</tr>
                  </thead>
                  <tbody>
                    {payloadKeys.map((k) => {
                      const cur = target && !corrField && PLACE_FIELD[k] ? show(PLACE_FIELD[k]!(target)) : null;
                      const v = show(c.payload[k]);
                      return (
                        <tr key={k}>
                          <th scope="row" className="whitespace-nowrap text-left text-sm font-medium">{FIELD_LABEL[k] ?? k} <span className="font-en text-xs text-muted">{k}</span></th>
                          <td className="break-words">{v}</td>
                          {target && !corrField && <td className={`break-words ${cur !== null && cur !== v ? 'bg-tint' : ''}`}>{cur ?? <span className="text-muted">—</span>}</td>}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : <EmptyState title="কোনো তথ্য নেই" />}
          </Card>

          {c.target_place_slug && (
            <Card title="লক্ষ্য স্থান" en="Target place">
              <div className="space-y-3 p-4 text-sm">
                {target ? (
                  <>
                    <KV items={[
                      ['নাম', <span key="n">{target.name_bn}{target.name_en && <span className="font-en text-muted"> · {target.name_en}</span>}</span>],
                      ['পাবলিক আইডি', <span key="p" className="font-en">{target.public_id} · /p/{target.slug}</span>],
                      ['এলাকা', target.area_label_bn],
                    ]} />
                    {corrField && (
                      <div className="overflow-x-auto">
                        <table className="table">
                          <thead><tr><th scope="col">ঘর <span className="font-en">{corrField}</span></th><th scope="col">রেকর্ডে এখন</th><th scope="col">জমাদাতার মতে বর্তমান</th><th scope="col">প্রস্তাবিত</th></tr></thead>
                          <tbody>
                            <tr>
                              <td>{FIELD_LABEL[corrField] ?? corrField}</td>
                              <td>{PLACE_FIELD[corrField] ? show(PLACE_FIELD[corrField]!(target)) : <span className="text-muted">অজানা ঘর</span>}</td>
                              <td>{show(c.payload.current_value)}</td>
                              <td className="bg-tint font-medium">{show(c.payload.proposed_value)}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    )}
                    <Link className="text-secondary hover:underline" href={`/places?q=${encodeURIComponent(target.public_id)}`}>অ্যাডমিনে স্থানটি খুলুন →</Link>
                  </>
                ) : (
                  <p>
                    <span className="font-en">/p/{c.target_place_slug}</span> — {targetNote}{' '}
                    <Link className="text-secondary hover:underline" href={`/places?q=${encodeURIComponent(String(c.payload.name_bn ?? ''))}`}>স্থান খুঁজুন</Link>
                  </p>
                )}
              </div>
            </Card>
          )}

          {(() => {
            const dups = (c as unknown as { duplicates?: { id: number; match_score: number; status: string; place_id: number; name_bn: string; name_en: string | null }[] }).duplicates ?? [];
            return dups.length ? (
              <Card title="সম্ভাব্য ডুপ্লিকেট" en="Possible duplicates">
                <ul className="divide-y divide-line text-sm">
                  {dups.map((d) => (
                    <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2">
                      <Link href={`/places/${d.place_id}`} className="text-secondary hover:underline">{d.name_bn}{d.name_en ? ` · ${d.name_en}` : ''}</Link>
                      <span className={d.match_score >= 95 ? 'text-danger' : 'text-warning'}>স্কোর {d.match_score} · {d.status}</span>
                    </li>
                  ))}
                </ul>
                <p className="px-4 pb-3 text-xs text-muted">অনুমোদনের আগে <Link href="/duplicates" className="underline">ডুপ্লিকেট</Link> পাতায় সিদ্ধান্ত নিন।</p>
              </Card>
            ) : null;
          })()}

          <Card title="প্রমাণ ও অবস্থান" en="Evidence & location">
            <div className="space-y-3 p-4 text-sm">
              {c.evidence?.length ? (
                <ul className="list-disc space-y-1 pl-5">
                  {c.evidence.map((e, i) => (
                    <li key={i}>
                      <a href={e.url} target="_blank" rel="noopener noreferrer nofollow" className="font-en break-all text-secondary hover:underline">{e.url}</a>
                      {e.note && <span className="text-muted"> — {e.note}</span>}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-muted">কোনো প্রমাণ-লিংক দেওয়া হয়নি।</p>}
              <KV items={[
                ['স্থানাঙ্ক', osm ? <span key="o" className="font-en">{c.lat}, {c.lon} · <a className="text-secondary hover:underline" href={osm} target="_blank" rel="noopener noreferrer nofollow">OpenStreetMap ↗</a></span> : null],
                ['প্রস্তাবিত এলাকা', c.target_area_id ? <Link key="a" className="font-en text-secondary hover:underline" href={`/areas/${c.target_area_id}`}>#{c.target_area_id}</Link> : null],
                ['জমাদাতা নিশ্চিত করেছেন', c.confirmed_accurate ? 'হ্যাঁ — তথ্য সঠিক বলে ঘোষণা' : 'না'],
                ['জমার সময়', formatDateTime(c.created_at)],
                ['শেষ পর্যালোচনা', c.reviewed_at ? formatDateTime(c.reviewed_at) : null],
                ['পর্যালোচকের নোট', c.reviewer_note],
              ]} />
            </div>
          </Card>

          <Card title="ঘটনাক্রম" en="Events">
            {c.events?.length ? (
              <ol className="divide-y divide-line">
                {c.events.map((e, i) => (
                  <li key={i} className="px-4 py-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs text-muted">{formatDateTime(e.at)}</span>
                      <span>{e.from_status ? CONTRIBUTION_STATUS_LABEL[e.from_status]?.bn : 'শুরু'} → <strong>{CONTRIBUTION_STATUS_LABEL[e.to_status]?.bn ?? e.to_status}</strong></span>
                      <span className="text-muted">· {e.actor_name ?? 'সিস্টেম'}</span>
                    </div>
                    {e.note && <p className="mt-1">{e.note}</p>}
                  </li>
                ))}
              </ol>
            ) : <EmptyState title="কোনো ঘটনা নেই" />}
          </Card>
        </div>

        <div>
          <Card title="সিদ্ধান্ত" en="Decision" className="xl:sticky xl:top-20">
            <div className="p-4">
              <DecisionForm action={decideContribution.bind(null, c.id)} status={c.status} type={c.type} suggestedAreaId={NEW_PLACE_TYPES.includes(c.type) ? c.target_area_id : null} />
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
