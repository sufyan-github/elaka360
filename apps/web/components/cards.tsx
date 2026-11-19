import { useLocale } from 'next-intl';
import { ChevronRight, MapPin } from 'lucide-react';
import type { AdminAreaSummary, Category, PlaceSummary } from '@elaka360/shared';
import { formatDistance, formatNumber, nameOf } from '@elaka360/shared';
import { Link } from '@/i18n/navigation';
import { areaHref } from '@/lib/links';
import { areaLabel, localName, otherLocale, otherName } from '@/lib/locale';
import { categoryColor, categoryIcon } from '@/lib/icons';
import { EvidenceBadge } from './ui';

/** Shared by server pages and client components (NearMe), so it reads the locale with a hook. */
export function AreaCard({ area, sub }: { area: AdminAreaSummary; sub?: string }) {
  const locale = useLocale();
  return (
    <Link href={areaHref(area)} className="group flex min-w-0 items-center justify-between gap-2 rounded-card border border-line bg-surface p-3 shadow-card hover:border-secondary">
      <span className="min-w-0">
        <span className="block truncate font-semibold">{nameOf(area, locale)}</span>
        <span className={`block truncate text-xs text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{nameOf(area, otherLocale(locale))}</span>
        {sub && <span className="mt-1 inline-block rounded-full bg-tint px-2 py-0.5 text-[11px] text-primary">{sub}</span>}
        {!area.production_eligible && <span className="mt-1 block"><EvidenceBadge level={area.evidence_level} /></span>}
      </span>
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-line group-hover:bg-tint">
        <ChevronRight className="h-4 w-4" />
      </span>
    </Link>
  );
}

export function CategoryTile({ category, count, href }: { category: Category; count?: number; href: string }) {
  const locale = useLocale();
  const Icon = categoryIcon(category.key);
  return (
    <Link href={href} className="flex flex-col items-center gap-1 rounded-card border border-line bg-surface px-2 py-3 text-center shadow-card hover:border-secondary">
      <Icon className="h-7 w-7" style={{ color: categoryColor(category.key) }} />
      <span className="text-[13px] leading-tight font-medium">{nameOf(category, locale)}</span>
      {count !== undefined && <span className="text-[11px] text-muted">({formatNumber(count, locale)})</span>}
    </Link>
  );
}

export function PlaceCard({ place }: { place: PlaceSummary }) {
  const locale = useLocale();
  const Icon = categoryIcon(place.category_key);
  const other = otherName(place, locale);
  const where = areaLabel(place, locale);
  return (
    <Link href={`/p/${place.slug}`} className="flex min-w-0 items-center gap-3 rounded-card border border-line bg-surface p-3 shadow-card hover:border-secondary">
      <span className="grid h-14 w-14 shrink-0 place-items-center rounded-chip bg-tint">
        <Icon className="h-7 w-7" style={{ color: categoryColor(place.category_key) }} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5">
          <span className="truncate font-semibold">{localName(place, locale)}</span>
        </span>
        {other && <span className={`block truncate text-xs text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{other}</span>}
        <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          {where && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" /> {where}
            </span>
          )}
          {place.distance_m !== undefined && <span>{formatDistance(place.distance_m, locale)}</span>}
          <EvidenceBadge level={place.evidence_level} compact />
        </span>
      </span>
      <ChevronRight className="h-4 w-4 shrink-0 text-muted" />
    </Link>
  );
}
