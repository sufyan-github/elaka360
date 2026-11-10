import Link from 'next/link';
import type { ReactNode } from 'react';
import { BadgeCheck, BookOpen, ChevronRight, CircleDashed, Info, TriangleAlert, Users } from 'lucide-react';
import type { AdminAreaSummary, DataSourceRef, EvidenceLevel } from '@elaka360/shared';
import { EVIDENCE_LABEL, formatDate, nameOf } from '@elaka360/shared';
import { areaHref } from '@/lib/links';

export function Section({ title, action, children, id }: { title: string; action?: { href: string; label: string }; children: ReactNode; id?: string }) {
  return (
    <section id={id} className="mt-6 scroll-mt-20">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-bold">{title}</h2>
        {action && (
          <Link href={action.href} className="flex items-center gap-1 text-sm font-medium text-secondary">
            {action.label} <ChevronRight className="h-4 w-4" />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-card border border-line bg-surface shadow-card ${className}`}>{children}</div>;
}

/**
 * Evidence badge. Only `official` evidence may say "verified" on its own (data trust policy);
 * secondary-source records say where the information comes from instead.
 */
export function EvidenceBadge({ level: raw, compact = false }: { level: EvidenceLevel | undefined; compact?: boolean }) {
  // Anything unknown is shown as not verified — never the other way round.
  const level: EvidenceLevel = raw && raw in EVIDENCE_LABEL ? raw : 'unverified';
  const l = EVIDENCE_LABEL[level];
  const style = {
    official: 'bg-tint text-verified',
    secondary: 'border border-line bg-surface text-ink',
    community: 'bg-warning-tint text-warning',
    unverified: 'bg-warning-tint text-warning',
  }[level];
  const Icon = { official: BadgeCheck, secondary: BookOpen, community: Users, unverified: CircleDashed }[level];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${style}`} title={l.hint_bn}>
      <Icon className="h-3.5 w-3.5" aria-hidden /> {compact && level === 'secondary' ? 'উৎসসহ' : l.bn}
    </span>
  );
}

/**
 * Shown at the top of any area or place that is not production-eligible: the record is public so people can
 * find and correct it, but it has not been checked against an official or reliable source.
 */
export function UnverifiedNotice({ level, reportHref }: { level: EvidenceLevel; reportHref: string }) {
  const why = level === 'community'
    ? 'কমিউনিটি ডেটাসেট বা ব্যবহারকারীর দেওয়া তথ্য থেকে নেওয়া'
    : 'এখনো কোনো উৎসের সঙ্গে মিলিয়ে দেখা হয়নি';
  return (
    <div role="note" className="mt-3 flex items-start gap-2 rounded-card border border-line bg-warning-tint p-3 text-sm">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
      <p>
        <strong className="text-warning">যাচাই করা হয়নি।</strong> এই তথ্য {why}; ভুল থাকতে পারে। গুরুত্বপূর্ণ কাজে সরকারি উৎস দেখে নিন।{' '}
        <Link href={reportHref} className="font-medium text-secondary underline">সঠিক তথ্য জানান</Link>
      </p>
    </div>
  );
}

export function Chip({ children, tone = 'tint' }: { children: ReactNode; tone?: 'tint' | 'line' }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs ${tone === 'tint' ? 'bg-tint text-primary' : 'border border-line text-ink'}`}>
      {children}
    </span>
  );
}

export function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  // value is pre-formatted with Bangla digits by the caller
  return (
    <div className="rounded-card border border-line bg-surface p-3 text-center">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-0.5 text-base font-bold">{value}</div>
      {sub && <div className="text-[11px] text-muted">{sub}</div>}
    </div>
  );
}

export function Breadcrumb({ items }: { items: AdminAreaSummary[] }) {
  return (
    <nav aria-label="অবস্থান" className="scrollbar-none -mx-4 overflow-x-auto px-4">
      <ol className="flex items-center gap-1 whitespace-nowrap text-sm text-muted">
        {items.map((a, i) => (
          <li key={a.id} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5" />}
            {i === items.length - 1 ? (
              <span className="text-ink">{nameOf(a, 'bn')}</span>
            ) : (
              <Link href={areaHref(a)} className="hover:text-primary">
                {nameOf(a, 'bn')}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function SourceFooter({ source, verifiedAt, note, evidence, reportHref }: {
  source: DataSourceRef | null; verifiedAt?: string | null; note?: string | null; evidence?: EvidenceLevel; reportHref?: string;
}) {
  return (
    <aside aria-label="তথ্যের উৎস ও যাচাই" className="mt-6 flex items-start gap-2 rounded-card border border-line bg-tint p-3 text-xs text-ink">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
      <div className="min-w-0 space-y-1">
        <div>
          তথ্যসূত্র:{' '}
          {source ? (
            source.url ? (
              <a href={source.url} target="_blank" rel="noopener noreferrer" className="font-medium text-secondary underline">
                {source.name}
              </a>
            ) : (
              <span className="font-medium">{source.name}</span>
            )
          ) : (
            'উল্লেখ নেই'
          )}
          {verifiedAt && <> · সর্বশেষ যাচাই: {formatDate(verifiedAt)}</>}
        </div>
        {evidence && EVIDENCE_LABEL[evidence] && (
          <div className="flex flex-wrap items-center gap-2">
            <EvidenceBadge level={evidence} /> <span className="text-muted">{EVIDENCE_LABEL[evidence].hint_bn}</span>
          </div>
        )}
        {note && <div className="text-muted">{note}</div>}
        {reportHref && (
          <Link href={reportHref} className="inline-block font-medium text-secondary underline">
            ভুল তথ্য জানান / সংশোধন প্রস্তাব করুন
          </Link>
        )}
      </div>
    </aside>
  );
}

export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <div className="rounded-card border border-dashed border-line bg-surface p-6 text-center">
      <div className="font-semibold">{title}</div>
      {body && <p className="mt-1 text-sm text-muted">{body}</p>}
    </div>
  );
}
