import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { ExternalLink, Hourglass, MapPin } from 'lucide-react';
import {
  CHILD_LEVELS, LEVEL_LABEL, formatArea, formatCompact, formatCount, formatNumber, nameOf, titleOf, type AdminLevel, type Locale,
} from '@elaka360/shared';
import { ApiError, api } from '@/lib/api';
import { asLocale, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { AreaCard, CategoryTile, PlaceCard } from '@/components/cards';
import { MapView } from '@/components/map/MapView';
import { SaveShare } from '@/components/client/SaveShare';
import { Breadcrumb, EmptyState, EvidenceBadge, Section, SourceFooter, StatTile, UnverifiedNotice } from '@/components/ui';

export const revalidate = 300;
/** Rendered on first request, then cached and revalidated (ISR). */
export async function generateStaticParams() {
  return [];
}

type Props = { params: Promise<{ locale: string; path: string[] }> };

async function load(segments: string[]) {
  const path = segments.map((s) => decodeURIComponent(s).toLowerCase()).join('/');
  if (!/^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(path)) return null;
  try {
    return await api.areaByPath(path);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 400)) return null;
    throw e;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const p = await params;
  const locale = asLocale(p.locale);
  const t = await getTranslations({ locale, namespace: 'Area' });
  const d = await load(p.path);
  if (!d) return { title: t('notFound') };
  const parent = d.breadcrumb.at(-2);
  const place = `${titleOf(d.area, locale)}${parent && parent.level !== 'country' ? `, ${nameOf(parent, locale)}` : ''}`;
  return {
    title: titleOf(d.area, locale),
    // Unverified records are public so people can correct them, but search engines should not index them.
    ...(d.area.production_eligible ? {} : { robots: { index: false, follow: true } }),
    description: t('description', { place }),
    alternates: localeAlternates(locale, `/${d.area.path}`),
  };
}

const POP_BASIS = { adjusted: 'popAdjusted', enumerated: 'popEnumerated', census: 'popCensus', estimate: 'popEstimate' } as const;

/** Level name for a count: "জেলা" in Bangla; "Districts" (or "District" for one) in English. */
function levelLabel(lvl: AdminLevel, locale: Locale, n = 2): string {
  const l = LEVEL_LABEL[lvl];
  return locale === 'bn' ? l.bn : n === 1 ? l.en : l.plural_en;
}

export default async function AreaPage({ params }: Props) {
  const p = await params;
  const locale = asLocale(p.locale);
  setRequestLocale(locale);
  const t = await getTranslations('Area');
  const d = await load(p.path);
  if (!d) notFound();
  const { area, breadcrumb, children, descendant_counts, pending_counts, place_counts } = d;
  const [categories, places] = await Promise.all([api.categories(), api.places({ areaId: area.id, limit: 12 })]);
  const parent = breadcrumb.at(-2);
  const district = area.level === 'district' ? area : breadcrumb.find((b) => b.level === 'district');
  const mapFocus = area.level === 'division' ? { divisionId: area.id } : district ? { districtIds: [district.id] } : {};
  const childLevels = (CHILD_LEVELS[area.level] ?? []).filter((l) => children.some((c) => c.level === l));
  const pending = Object.entries(pending_counts).filter(([, n]) => n) as [AdminLevel, number][];

  const popBasis = POP_BASIS[(area.population_basis ?? '') as keyof typeof POP_BASIS] ?? 'popCensus';
  const stats: { label: string; value: string; sub?: string }[] = [];
  if (area.area_km2) stats.push({ label: t('area'), value: formatArea(area.area_km2, locale), sub: area.area_basis === 'computed_from_polygon' ? t('areaComputed') : undefined });
  if (area.population_2022) stats.push({ label: t('population'), value: formatCompact(area.population_2022, locale), sub: t(popBasis) });
  for (const lvl of ['district', 'upazila', 'city_corporation', 'union', 'pourashava'] as AdminLevel[]) {
    const n = descendant_counts[lvl];
    if (n) stats.push({ label: levelLabel(lvl, locale, n), value: formatCount(n, locale) });
  }
  if (area.wards_count) stats.push({ label: levelLabel('ward', locale, area.wards_count), value: formatCount(area.wards_count, locale) });
  const pendingList = pending
    .map(([lvl, n]) => `${formatCount(n, locale)} ${locale === 'bn' ? LEVEL_LABEL[lvl].bn : levelLabel(lvl, locale, n).toLowerCase()}`)
    .join(t('and'));

  return (
    <>
      <div className="pt-4">
        <Breadcrumb items={breadcrumb} />
      </div>
      <section className="hero-green mt-3 rounded-card px-5 py-6">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold md:text-3xl">{titleOf(area, locale)}</h1>
          <span className="rounded-full bg-white">
            <EvidenceBadge level={area.evidence_level} compact />
          </span>
        </div>
        <p lang={otherLocale(locale)} className={`text-sm text-white/80 ${locale === 'bn' ? 'font-en' : ''}`}>{titleOf(area, otherLocale(locale))}</p>
        {parent && parent.level !== 'country' && (
          <p className="mt-2 flex items-center gap-1 text-sm text-white/90">
            <MapPin className="h-4 w-4" aria-hidden /> {breadcrumb.slice(1, -1).reverse().map((b) => titleOf(b, locale)).join(', ')}
          </p>
        )}
      </section>

      {!area.production_eligible && (
        <UnverifiedNotice level={area.evidence_level} reportHref={`/contribute/new?type=correction&area=${encodeURIComponent(area.path)}`} />
      )}

      <div className="mt-3 grid grid-cols-2 gap-2 sm:max-w-xs">
        <SaveShare areaPath={area.path} title={titleOf(area, locale)} />
      </div>

      {stats.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {stats.map((s) => <StatTile key={s.label} {...s} />)}
        </div>
      )}
      {area.population_basis === 'enumerated' && (
        <p className="mt-2 text-xs text-muted">{t('enumeratedNote')}</p>
      )}

      {childLevels.map((lvl) => {
        const list = children.filter((c) => c.level === lvl);
        return (
          <Section key={lvl} id={lvl} title={`${LEVEL_LABEL[lvl][locale === 'bn' ? 'plural_bn' : 'plural_en']} (${formatNumber(list.length, locale)})`}>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {list.map((c) => <AreaCard key={c.id} area={c} />)}
            </div>
          </Section>
        );
      })}

      {pending.length > 0 && (
        <div className="mt-6 flex items-start gap-2 rounded-card border border-line bg-warning-tint p-3 text-sm">
          <Hourglass className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
          <p>
            {t.rich('pending', {
              list: pendingList,
              link: (c) => <Link href="/data-policy" className="font-medium text-secondary underline">{c}</Link>,
            })}
          </p>
        </div>
      )}

      <Section title={t('map')} id="map" action={{ href: '/map', label: t('fullMap') }}>
        <MapView {...mapFocus} areaId={area.id} className="h-72 md:h-96" />
      </Section>

      <Section title={t('quickSearch')} id="categories">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
          {categories.map((c) => (
            <CategoryTile key={c.id} category={c} count={place_counts[c.key] ?? 0} href={`/c/${c.key}?area=${area.id}`} />
          ))}
        </div>
      </Section>

      <Section title={t('placesTitle')} id="places">
        {places.items.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {places.items.map((p) => <PlaceCard key={p.public_id} place={p} />)}
          </div>
        ) : (
          <EmptyState title={t('emptyTitle')} body={t('emptyBody')} />
        )}
        <Link href={`/contribute/new?type=new_place&area=${encodeURIComponent(area.path)}`} className="mt-3 inline-block text-sm font-medium text-secondary underline">
          {t('addPlace')}
        </Link>
      </Section>

      {area.website && (
        <a href={area.website} target="_blank" rel="noopener noreferrer" className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-secondary underline">
          {t('website')} <ExternalLink className="h-4 w-4" aria-hidden />
        </a>
      )}
      <SourceFooter
        source={area.evidence_source ?? area.source}
        verifiedAt={area.last_reviewed_at}
        note={area.notes}
        evidence={area.evidence_level}
        reportHref={`/contribute/new?type=correction&area=${encodeURIComponent(area.path)}`}
      />
    </>
  );
}
