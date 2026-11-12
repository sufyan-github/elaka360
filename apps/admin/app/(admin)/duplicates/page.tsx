import Link from 'next/link';
import { EVIDENCE_LABEL, formatNumber, toBnDigits, type EvidenceLevel } from '@elaka360/shared';
import { decideDuplicate, scanDuplicates } from '../actions';
import { ActionForm, SubmitButton } from '@/components/ActionForm';
import { Card, EmptyState, ErrorPanel, PageHeader } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';

export const metadata = { title: 'ডুপ্লিকেট' };

interface PlaceBrief { id: number; slug: string; name_bn: string; name_en: string | null; status: string; evidence_level: EvidenceLevel; production_eligible: boolean; lat: number | null; lon: number | null }
interface Candidate {
  id: number; status: string; match_score: number; contribution_id: number | null;
  match_detail: { name_similarity?: number; distance_m?: number | null } | null; place_a: PlaceBrief; place_b: PlaceBrief | null;
}

const TABS = [['open', 'খোলা'], ['needs_more_review', 'আরও পর্যালোচনা'], ['merged', 'একত্রিত'], ['not_duplicate', 'ডুপ্লিকেট নয়'], ['kept_separate', 'আলাদা রাখা']] as const;

function Side({ p, label }: { p: PlaceBrief; label: string }) {
  return (
    <div className="min-w-0 rounded-chip border border-line p-3 text-sm">
      <div className="text-xs text-muted">{label}</div>
      <Link href={`/places/${p.id}`} className="font-semibold text-secondary hover:underline">{p.name_bn}</Link>
      {p.name_en && <div className="font-en text-xs text-muted">{p.name_en}</div>}
      <div className="mt-1 text-xs">{EVIDENCE_LABEL[p.evidence_level]?.bn ?? p.evidence_level} · {p.production_eligible ? 'উৎসসহ' : 'যাচাই হয়নি'} · {p.status}</div>
      {p.lat !== null && <div className="font-en text-xs text-muted">{p.lat}, {p.lon}</div>}
    </div>
  );
}

export default async function DuplicatesPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { ok, can } = await access('places.read');
  if (!ok) return <Forbidden perm="places.read" />;
  const { status: raw } = await searchParams;
  const status = TABS.some(([k]) => k === raw) ? raw! : 'open';
  const r = await apiTry<{ items: Candidate[]; total: number }>(`/v1/admin/duplicates?status=${status}&limit=100`);
  const canEdit = can('places.edit');
  return (
    <>
      <PageHeader title="সম্ভাব্য ডুপ্লিকেট" en="Duplicates">
        {r.data && <span className="text-sm text-muted">{formatNumber(r.data.total)}টি</span>}
      </PageHeader>
      <p className="mb-4 text-sm text-muted">
        নাম (বাংলা ও ইংরেজি) ও ৫০০ মিটারের মধ্যে দূরত্ব মিলিয়ে স্কোর। ৯৫ বা বেশি হলে সিদ্ধান্ত না হওয়া পর্যন্ত স্থানটি প্রকাশ করা যায় না; ৮০–৯৫ পর্যালোচনার জন্য।
      </p>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <nav aria-label="অবস্থা" className="flex flex-wrap gap-2">
          {TABS.map(([k, l]) => (
            <Link key={k} href={`/duplicates?status=${k}`} aria-current={status === k ? 'page' : undefined} className={`btn ${status === k ? 'btn-primary' : 'btn-outline'}`}>{l}</Link>
          ))}
        </nav>
        {canEdit && (
          <ActionForm action={scanDuplicates} className="ml-auto">
            <SubmitButton variant="outline" confirm="সব সক্রিয় স্থান আবার পরীক্ষা করবেন?">সব স্থান আবার পরীক্ষা · Re-scan</SubmitButton>
          </ActionForm>
        )}
      </div>
      {r.error ? <ErrorPanel error={r.error} /> : !r.data.items.length ? (
        <Card><EmptyState title="কোনো সম্ভাব্য ডুপ্লিকেট নেই" /></Card>
      ) : (
        <ul className="space-y-3">
          {r.data.items.map((d) => (
            <li key={d.id}>
              <Card>
                <div className="grid gap-4 p-4 lg:grid-cols-[1fr_16rem]">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <strong className={d.match_score >= 95 ? 'text-danger' : 'text-warning'}>স্কোর {toBnDigits(d.match_score)}</strong>
                      {d.match_score >= 95 && <span className="rounded-full bg-danger-tint px-2 py-0.5 text-xs text-danger">প্রকাশ আটকে আছে</span>}
                      {d.match_detail && (
                        <span className="text-xs text-muted">
                          নামের মিল {toBnDigits(Math.round((d.match_detail.name_similarity ?? 0) * 100))}%
                          {d.match_detail.distance_m != null ? ` · দূরত্ব ${toBnDigits(Math.round(d.match_detail.distance_m))} মি` : ' · অবস্থান নেই'}
                        </span>
                      )}
                    </div>
                    <div className="grid gap-2 md:grid-cols-2">
                      <Side p={d.place_a} label="A — রাখা হবে (বিদ্যমান)" />
                      {d.place_b ? <Side p={d.place_b} label="B — নতুন / সম্ভাব্য অনুলিপি" /> : (
                        <div className="rounded-chip border border-dashed border-line p-3 text-sm">
                          <div className="text-xs text-muted">B — অবদান</div>
                          <Link href={`/moderation/${d.contribution_id}`} className="text-secondary hover:underline">অবদান #{toBnDigits(d.contribution_id ?? 0)}</Link>
                        </div>
                      )}
                    </div>
                  </div>
                  {canEdit && (d.status === 'open' || d.status === 'needs_more_review') && (
                    <ActionForm action={decideDuplicate.bind(null, d.id)} className="flex flex-col gap-2">
                      <label className="text-sm">
                        <span className="mb-1 block font-medium">নোট</span>
                        <textarea name="note" required minLength={3} maxLength={1000} rows={2} className="input" />
                      </label>
                      <SubmitButton variant="danger" name="decision" value="merged"
                        confirm={d.place_b ? 'B আর্কাইভ হবে এবং তার রিভিউ/সংরক্ষণ A-তে যাবে। নিশ্চিত?' : 'অবদানটি ডুপ্লিকেট হিসেবে বাতিল হবে। নিশ্চিত?'}>
                        {d.place_b ? 'একত্রিত করুন (A রাখুন)' : 'ডুপ্লিকেট — বাতিল'}
                      </SubmitButton>
                      <SubmitButton variant="outline" name="decision" value="not_duplicate">ডুপ্লিকেট নয়</SubmitButton>
                      <SubmitButton variant="outline" name="decision" value="kept_separate">আলাদা রাখুন</SubmitButton>
                      <SubmitButton variant="outline" name="decision" value="needs_more_review">আরও পর্যালোচনা</SubmitButton>
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
