import Link from 'next/link';
import type { ReactNode } from 'react';
import { BadgeCheck, ChevronRight, Info } from 'lucide-react';
import type { AdminAreaSummary, DataSourceRef } from '@elaka360/shared';
import { formatDate, nameOf } from '@elaka360/shared';
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

export function VerifiedBadge({ label = 'যাচাইকৃত' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-tint px-2 py-0.5 text-xs font-medium text-verified">
      <BadgeCheck className="h-3.5 w-3.5" /> {label}
    </span>
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

export function SourceFooter({ source, verifiedAt, note }: { source: DataSourceRef | null; verifiedAt?: string | null; note?: string | null }) {
  return (
    <div className="mt-6 flex items-start gap-2 rounded-card border border-line bg-tint p-3 text-xs text-ink">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
      <div>
        <div>
          তথ্যসূত্র:{' '}
          {source ? (
            source.url ? (
              <a href={source.url} target="_blank" rel="noreferrer" className="font-medium text-secondary underline">
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
        {note && <div className="mt-1 text-muted">{note}</div>}
      </div>
    </div>
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
