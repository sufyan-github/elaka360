import Link from 'next/link';
import type { AdminStats, EvidenceLevel } from '@elaka360/shared';
import { formatNumber } from '@elaka360/shared';
import { AuditTable } from '@/components/Audit';
import { Card, ErrorPanel, EvidenceBadge, PageHeader } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import { EVIDENCE_LEVELS } from '@/lib/labels';

export const metadata = { title: 'ড্যাশবোর্ড' };

function Tile({ label, en, value, sub, href }: { label: string; en: string; value: number; sub?: string; href?: string }) {
  const body = (
    <>
      <div className="text-sm text-muted">{label} <span className="font-en text-xs">· {en}</span></div>
      <div className="mt-1 text-3xl font-bold tabular-nums">{formatNumber(value)}</div>
      {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
    </>
  );
  const cls = 'block rounded-card border border-line bg-surface p-4 shadow-card';
  return href ? <Link href={href} className={`${cls} hover:border-secondary`}>{body}</Link> : <div className={cls}>{body}</div>;
}

/** Share as a whole percent; a non-zero share under 0.5% shows as "<১%" rather than a misleading 0%. */
const pct = (n: number, d: number) => {
  if (d <= 0) return '—';
  const p = (n / d) * 100;
  return n > 0 && p < 0.5 ? `<${formatNumber(1)}%` : `${formatNumber(Math.round(p))}%`;
};

/** Counts per evidence tier, each with its share of the total. One hue; the label and number carry identity. */
function EvidenceBreakdown({ title, en, data, total, link }: { title: string; en: string; data: Record<EvidenceLevel, number>; total: number; link: string }) {
  return (
    <Card title={title} en={en}>
      <ul className="space-y-3 p-4">
        {EVIDENCE_LEVELS.map((lvl) => {
          const n = data[lvl] ?? 0;
          const share = total > 0 ? (n / total) * 100 : 0;
          return (
            <li key={lvl}>
              <div className="flex items-center justify-between gap-2 text-sm">
                <Link href={`${link}?evidence=${lvl}`} className="hover:underline"><EvidenceBadge level={lvl} /></Link>
                <span className="tabular-nums"><strong>{formatNumber(n)}</strong> <span className="text-muted">({pct(n, total)})</span></span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-tint" aria-hidden>
                <div className="h-full rounded-full bg-secondary" style={{ width: `${share}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

export default async function Dashboard() {
  const { ok, can } = await access('stats.read');
  if (!ok) return <Forbidden perm="stats.read" />;
  const r = await apiTry<AdminStats>('/v1/admin/stats');
  return (
    <>
      <PageHeader title="ড্যাশবোর্ড" en="Dashboard" />
      {r.error ? <ErrorPanel error={r.error} /> : (
        <>
          <p className="mb-4 text-sm text-muted">সব সংখ্যা সরাসরি ডেটাবেস থেকে গণনা করা (<code className="font-en">/v1/admin/stats</code>)। “প্রকাশিত” মানে সরকারি বা দ্বিতীয় উৎসসহ যাচাই করা, জনসাধারণের জন্য দৃশ্যমান রেকর্ড।</p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            <Tile label="মোট এলাকা" en="Areas" value={r.data.areas_total} sub={`প্রকাশিত ${formatNumber(r.data.areas_public)} (${pct(r.data.areas_public, r.data.areas_total)})`} href={can('areas.read') ? '/areas' : undefined} />
            <Tile label="সক্রিয় স্থান" en="Active places" value={r.data.places_total} sub={`প্রকাশিত ${formatNumber(r.data.places_public)} (${pct(r.data.places_public, r.data.places_total)})`} href={can('places.read') ? '/places' : undefined} />
            <Tile label="অপেক্ষমাণ অবদান" en="Pending contributions" value={r.data.contributions_pending} sub="নতুন ও পর্যালোচনায়" href={can('contributions.moderate') ? '/moderation' : undefined} />
            <Tile label="খোলা রিভিউ রিপোর্ট" en="Open review reports" value={r.data.review_reports_open} href={can('reviews.moderate') ? '/review-reports' : undefined} />
            <Tile label="সম্ভাব্য ডুপ্লিকেট" en="Open duplicates" value={r.data.duplicate_candidates_open} />
            <Tile label="ডেটা মানের সমস্যা" en="Open quality issues" value={r.data.quality_issues_open} />
            <Tile label="সক্রিয় ব্যবহারকারী (৩০ দিন)" en="Active users 30d" value={r.data.users_active_30d} href={can('users.manage') ? '/users' : undefined} />
            <Tile label="অপ্রকাশিত এলাকা" en="Areas not public" value={Math.max(0, r.data.areas_total - r.data.areas_public)} sub="যাচাই কেন্দ্রে দেখুন" href={can('verify') ? '/verification' : undefined} />
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <EvidenceBreakdown title="এলাকা: প্রমাণের স্তর" en="Areas by evidence" data={r.data.areas_by_evidence} total={r.data.areas_total} link="/areas" />
            <EvidenceBreakdown title="স্থান: প্রমাণের স্তর" en="Places by evidence" data={r.data.places_by_evidence} total={r.data.places_total} link="/places" />
          </div>
          <Card title="সাম্প্রতিক কার্যক্রম" en="Recent activity" className="mt-4"
            action={can('audit.read') ? <Link href="/audit" className="text-sm text-secondary hover:underline">সব দেখুন</Link> : undefined}>
            <AuditTable items={r.data.recent_activity} empty="এখনো কোনো কার্যক্রম নেই" />
          </Card>
        </>
      )}
    </>
  );
}
