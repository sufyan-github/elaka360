import type { ReactNode } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { BadgeCheck, BookOpen, ChevronRight, CircleDashed, Info, TriangleAlert, Users } from 'lucide-react';
import type { AdminAreaSummary, DataSourceRef, EvidenceLevel } from '@elaka360/shared';
import { EVIDENCE_LABEL, formatDate, nameOf } from '@elaka360/shared';
import { Link } from '@/i18n/navigation';
import { areaHref } from '@/lib/links';
import { evidenceText } from '@/lib/locale';

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
  const locale = useLocale();
  const t = useTranslations('Evidence');
  // Anything unknown is shown as not verified — never the other way round.
  const level: EvidenceLevel = raw && raw in EVIDENCE_LABEL ? raw : 'unverified';
  const l = evidenceText(level, locale);
  const style = {
    official: 'bg-tint text-verified',
    secondary: 'border border-line bg-surface text-ink',
    community: 'bg-warning-tint text-warning',
    unverified: 'bg-warning-tint text-warning',
  }[level];
  const Icon = { official: BadgeCheck, secondary: BookOpen, community: Users, unverified: CircleDashed }[level];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${style}`} title={l.hint}>
      <Icon className="h-3.5 w-3.5" aria-hidden /> {compact && level === 'secondary' ? t('sourced') : l.label}
    </span>
  );
}

/**
 * Shown at the top of any area or place that is not production-eligible: the record is public so people can
 * find and correct it, but it has not been checked against an official or reliable source.
 */
export function UnverifiedNotice({ level, reportHref }: { level: EvidenceLevel; reportHref: string }) {
  const t = useTranslations('Evidence');
  return (
    <div role="note" className="mt-3 flex items-start gap-2 rounded-card border border-line bg-warning-tint p-3 text-sm">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
      <p>
        <strong className="text-warning">{t('noticeTitle')}</strong> {level === 'community' ? t('noticeCommunity') : t('noticeUnverified')}{' '}
        <Link href={reportHref} className="font-medium text-secondary underline">{t('noticeReport')}</Link>
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
  // value is pre-formatted in the page's locale by the caller
  return (
    <div className="rounded-card border border-line bg-surface p-3 text-center">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-0.5 text-base font-bold">{value}</div>
      {sub && <div className="text-[11px] text-muted">{sub}</div>}
    </div>
  );
}

export function Breadcrumb({ items }: { items: AdminAreaSummary[] }) {
  const locale = useLocale();
  const t = useTranslations('Common');
  return (
    <nav aria-label={t('breadcrumb')} className="scrollbar-none -mx-4 overflow-x-auto px-4">
      <ol className="flex items-center gap-1 whitespace-nowrap text-sm text-muted">
        {items.map((a, i) => (
          <li key={a.id} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5" />}
            {i === items.length - 1 ? (
              <span className="text-ink">{nameOf(a, locale)}</span>
            ) : (
              <Link href={areaHref(a)} className="hover:text-primary">
                {nameOf(a, locale)}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function SourceLink({ source }: { source: DataSourceRef }) {
  return source.url ? (
    <a href={source.url} target="_blank" rel="noopener noreferrer" className="font-medium text-secondary underline">
      {source.name}
    </a>
  ) : (
    <span className="font-medium">{source.name}</span>
  );
}

export function SourceFooter({ source, detailsSource, verifiedAt, note, evidence, reportHref }: {
  source: DataSourceRef | null; detailsSource?: DataSourceRef | null; verifiedAt?: string | null; note?: string | null;
  evidence?: EvidenceLevel; reportHref?: string;
}) {
  const locale = useLocale();
  const t = useTranslations('Evidence');
  return (
    <aside aria-label={t('sourceLabel')} className="mt-6 flex items-start gap-2 rounded-card border border-line bg-tint p-3 text-xs text-ink">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
      <div className="min-w-0 space-y-1">
        <div>
          {t('source')}{' '}
          {source ? <SourceLink source={source} /> : t('sourceMissing')}
          {verifiedAt && <> · {t('lastChecked', { date: formatDate(verifiedAt, locale) })}</>}
        </div>
        {detailsSource && (
          <div>
            {t('detailsFrom')} <SourceLink source={detailsSource} />
          </div>
        )}
        {evidence && EVIDENCE_LABEL[evidence] && (
          <div className="flex flex-wrap items-center gap-2">
            <EvidenceBadge level={evidence} /> <span className="text-muted">{evidenceText(evidence, locale).hint}</span>
          </div>
        )}
        {note && <div className="text-muted">{note}</div>}
        {reportHref && (
          <Link href={reportHref} className="inline-block font-medium text-secondary underline">
            {t('report')}
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
