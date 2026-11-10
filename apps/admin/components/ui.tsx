import Link from 'next/link';
import type { ReactNode } from 'react';
import { AlertTriangle, BadgeCheck, BookOpen, CircleDashed, Eye, EyeOff, Inbox } from 'lucide-react';
import type { EvidenceLevel } from '@elaka360/shared';
import { EVIDENCE_LABEL, formatDate, toBnDigits } from '@elaka360/shared';
import { STATUS_LABEL } from '@/lib/labels';

export function PageHeader({ title, en, children, back }: { title: string; en?: string; children?: ReactNode; back?: { href: string; label: string } }) {
  return (
    <div className="mb-5">
      {back && <Link href={back.href} className="mb-1 inline-block text-sm text-secondary hover:underline">← {back.label}</Link>}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-bold">
          {title}
          {en && <span className="font-en ml-2 text-base font-normal text-muted">{en}</span>}
        </h1>
        {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
      </div>
    </div>
  );
}

export function Card({ children, className = '', title, en, action }: { children: ReactNode; className?: string; title?: string; en?: string; action?: ReactNode }) {
  return (
    <section className={`rounded-card border border-line bg-surface shadow-card ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
          <h2 className="font-semibold">{title}{en && <span className="font-en ml-2 text-xs font-normal text-muted">{en}</span>}</h2>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

const EVIDENCE_TONE: Record<EvidenceLevel, string> = {
  official: 'bg-tint text-verified border-verified/30',
  secondary: 'bg-tint text-primary border-line',
  community: 'bg-surface text-ink border-line border-dashed',
  unverified: 'bg-surface text-muted border-line border-dashed',
};

/** Evidence tier badge. Community/unverified never look "verified": no check icon, dashed border. */
export function EvidenceBadge({ level }: { level: EvidenceLevel }) {
  const l = EVIDENCE_LABEL[level];
  const Icon = level === 'official' ? BadgeCheck : level === 'secondary' ? BookOpen : CircleDashed;
  return (
    <span title={l.hint_bn} className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${EVIDENCE_TONE[level]}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden /> {l.bn}
    </span>
  );
}

export function PublicBadge({ eligible }: { eligible: boolean }) {
  return eligible ? (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-tint px-2 py-0.5 text-xs font-medium text-primary">
      <Eye className="h-3.5 w-3.5" aria-hidden /> প্রকাশিত
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border border-line px-2 py-0.5 text-xs text-muted">
      <EyeOff className="h-3.5 w-3.5" aria-hidden /> অপ্রকাশিত
    </span>
  );
}

export function Chip({ children, tone = 'line' }: { children: ReactNode; tone?: 'line' | 'tint' | 'danger' }) {
  const cls = tone === 'tint' ? 'bg-tint text-primary' : tone === 'danger' ? 'bg-danger-tint text-danger' : 'border border-line text-ink';
  return <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs ${cls}`}>{children}</span>;
}

export function StatusChip({ status }: { status: string }) {
  const tone = ['active', 'approved', 'upheld'].includes(status) ? 'tint' : ['suspended', 'rejected', 'closed'].includes(status) ? 'danger' : 'line';
  return <Chip tone={tone}>{STATUS_LABEL[status] ?? status}</Chip>;
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-12 text-center">
      <Inbox className="h-8 w-8 text-muted" aria-hidden />
      <p className="font-medium">{title}</p>
      {hint && <p className="max-w-md text-sm text-muted">{hint}</p>}
    </div>
  );
}

export function ErrorPanel({ error, title = 'তথ্য আনা যায়নি' }: { error: { status?: number; detail?: string; message?: string; requestId?: string }; title?: string }) {
  return (
    <div role="alert" className="flex gap-3 rounded-card border border-danger/30 bg-danger-tint p-4 text-sm">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-danger" aria-hidden />
      <div>
        <p className="font-semibold text-danger">{title}{error.status ? ` (${error.status})` : ''}</p>
        <p className="mt-1">{error.detail ?? error.message}</p>
        {error.requestId && <p className="font-en mt-1 text-xs text-muted">request_id: {error.requestId}</p>}
      </div>
    </div>
  );
}

export function KV({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[minmax(7rem,auto)_1fr] gap-x-4 gap-y-2 text-sm">
      {items.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted">{k}</dt>
          <dd className="min-w-0 break-words">{v === null || v === undefined || v === '' ? <span className="text-muted">—</span> : v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** "2026-11-09T10:22:00Z" → "৯ নভেম্বর ২০২৬, ১০:২২ UTC" (times are kept in UTC as returned by the API). */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const m = /T(\d{2}):(\d{2})/.exec(iso);
  return m ? `${formatDate(iso)}, ${toBnDigits(`${m[1]}:${m[2]}`)} UTC` : formatDate(iso);
}

/** Cursor pagination: "next" from the API's next_cursor; back to the first page (cursors are forward-only). */
export function Pager({ basePath, params, nextCursor, hasCursor }: { basePath: string; params: Record<string, string | undefined>; nextCursor: string | null; hasCursor: boolean }) {
  const href = (cursor?: string) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v && k !== 'cursor') p.set(k, v);
    if (cursor) p.set('cursor', cursor);
    const s = p.toString();
    return s ? `${basePath}?${s}` : basePath;
  };
  if (!nextCursor && !hasCursor) return null;
  return (
    <nav aria-label="পাতা" className="flex items-center justify-between gap-2 border-t border-line px-4 py-3 text-sm">
      {hasCursor ? <Link className="btn btn-outline btn-sm" href={href()}>« প্রথম পাতা</Link> : <span />}
      {nextCursor ? <Link className="btn btn-outline btn-sm" href={href(nextCursor)} rel="next">পরের পাতা »</Link> : <span className="text-muted">শেষ পাতা</span>}
    </nav>
  );
}

/** A GET filter form: works without JavaScript, keeps the URL shareable. */
export function FilterBar({ children, action, resetHref }: { children: ReactNode; action: string; resetHref: string }) {
  return (
    <form action={action} method="get" role="search" className="mb-4 flex flex-wrap items-end gap-3 rounded-card border border-line bg-surface p-3">
      {children}
      <div className="flex gap-2">
        <button type="submit" className="btn btn-primary">ফিল্টার</button>
        <Link href={resetHref} className="btn btn-outline">মুছুন</Link>
      </div>
    </form>
  );
}

export function FilterField({ label, htmlFor, children, wide }: { label: string; htmlFor: string; children: ReactNode; wide?: boolean }) {
  return (
    <div className={wide ? 'min-w-[14rem] flex-1' : 'min-w-[9rem]'}>
      <label htmlFor={htmlFor} className="mb-1 block text-xs font-medium text-muted">{label}</label>
      {children}
    </div>
  );
}

export function TableWrap({ children }: { children: ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

