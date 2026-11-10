import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { ExternalLink, Hourglass, MapPin } from 'lucide-react';
import {
  CHILD_LEVELS, LEVEL_LABEL, formatArea, formatCompact, formatCount, formatNumber, nameOf, titleOf, type AdminLevel,
} from '@elaka360/shared';
import { ApiError, api } from '@/lib/api';
import { AreaCard, CategoryTile, PlaceCard } from '@/components/cards';
import { MapView } from '@/components/map/MapView';
import { SaveShare } from '@/components/client/SaveShare';
import { Breadcrumb, EmptyState, EvidenceBadge, Section, SourceFooter, StatTile } from '@/components/ui';

export const revalidate = 300;
/** Rendered on first request, then cached and revalidated (ISR). */
export async function generateStaticParams() {
  return [];
}

type Props = { params: Promise<{ path: string[] }> };

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
  const d = await load((await params).path);
  if (!d) return { title: 'এলাকা পাওয়া যায়নি' };
  const parent = d.breadcrumb.at(-2);
  return {
    title: titleOf(d.area, 'bn'),
    description: `${titleOf(d.area, 'bn')}${parent && parent.level !== 'country' ? `, ${nameOf(parent, 'bn')}` : ''} — প্রশাসনিক তথ্য, প্রতিষ্ঠান, সেবা ও দর্শনীয় স্থান, উৎসসহ।`,
  };
}

const POP_BASIS: Record<string, string> = { adjusted: 'জনশুমারি ২০২২ (সমন্বিত)', enumerated: 'জনশুমারি ২০২২ (গণনাকৃত)', census: 'জনশুমারি ২০২২', estimate: 'প্রাক্কলন' };

export default async function AreaPage({ params }: Props) {
  const d = await load((await params).path);
  if (!d) notFound();
  const { area, breadcrumb, children, descendant_counts, pending_counts, place_counts } = d;
  const [categories, places] = await Promise.all([api.categories(), api.places({ areaId: area.id, limit: 12 })]);
  const parent = breadcrumb.at(-2);
  const district = area.level === 'district' ? area : breadcrumb.find((b) => b.level === 'district');
  const mapFocus = area.level === 'division' ? { divisionId: area.id } : district ? { districtIds: [district.id] } : {};
  const childLevels = (CHILD_LEVELS[area.level] ?? []).filter((l) => children.some((c) => c.level === l));
  const pending = Object.entries(pending_counts).filter(([, n]) => n) as [AdminLevel, number][];

  const stats: { label: string; value: string; sub?: string }[] = [];
  if (area.area_km2) stats.push({ label: 'আয়তন', value: formatArea(area.area_km2), sub: area.area_basis === 'computed_from_polygon' ? 'মানচিত্র থেকে আনুমানিক' : undefined });
  if (area.population_2022) stats.push({ label: 'জনসংখ্যা', value: formatCompact(area.population_2022), sub: POP_BASIS[area.population_basis ?? ''] ?? 'জনশুমারি ২০২২' });
  for (const lvl of ['district', 'upazila', 'city_corporation', 'union', 'pourashava'] as AdminLevel[]) {
    const n = descendant_counts[lvl];
    if (n) stats.push({ label: LEVEL_LABEL[lvl].bn, value: formatCount(n) });
  }
  if (area.wards_count) stats.push({ label: 'ওয়ার্ড', value: formatCount(area.wards_count) });

  return (
    <>
      <div className="pt-4">
        <Breadcrumb items={breadcrumb} />
      </div>
      <section className="hero-green mt-3 rounded-card px-5 py-6">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold md:text-3xl">{titleOf(area, 'bn')}</h1>
          <span className="rounded-full bg-white">
            <EvidenceBadge level={area.evidence_level} compact />
          </span>
        </div>
        <p className="font-en text-sm text-white/80">{titleOf(area, 'en')}</p>
        {parent && parent.level !== 'country' && (
          <p className="mt-2 flex items-center gap-1 text-sm text-white/90">
            <MapPin className="h-4 w-4" aria-hidden /> {breadcrumb.slice(1, -1).reverse().map((b) => titleOf(b, 'bn')).join(', ')}
          </p>
        )}
      </section>

      <div className="mt-3 grid grid-cols-2 gap-2 sm:max-w-xs">
        <SaveShare areaPath={area.path} title={titleOf(area, 'bn')} />
      </div>

      {stats.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {stats.map((s) => <StatTile key={s.label} {...s} />)}
        </div>
      )}
      {area.population_basis === 'enumerated' && (
        <p className="mt-2 text-xs text-muted">এই এলাকার জনসংখ্যা গণনাকৃত হিসাব; জেলা ও বিভাগের সংখ্যা সমন্বিত হিসাব, তাই যোগফল হুবহু মিলবে না।</p>
      )}

      {childLevels.map((lvl) => {
        const list = children.filter((c) => c.level === lvl);
        return (
          <Section key={lvl} id={lvl} title={`${LEVEL_LABEL[lvl].plural_bn} (${formatNumber(list.length)})`}>
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
            এই এলাকার{' '}
            {pending.map(([lvl, n], i) => (
              <span key={lvl}>{i > 0 && ' ও '}{formatCount(n)} {LEVEL_LABEL[lvl].bn}</span>
            ))}
            -এর তথ্য আছে, কিন্তু সরকারি বা নির্ভরযোগ্য উৎসের সঙ্গে মিলিয়ে দেখা শেষ না হওয়া পর্যন্ত দেখানো হচ্ছে না।{' '}
            <Link href="/data-policy" className="font-medium text-secondary underline">কেন?</Link>
          </p>
        </div>
      )}

      <Section title="মানচিত্র" id="map" action={{ href: '/map', label: 'পূর্ণ মানচিত্র' }}>
        <MapView {...mapFocus} areaId={area.id} className="h-72 md:h-96" />
      </Section>

      <Section title="দ্রুত অনুসন্ধান" id="categories">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
          {categories.map((c) => (
            <CategoryTile key={c.id} category={c} count={place_counts[c.key] ?? 0} href={`/c/${c.key}?area=${area.id}`} />
          ))}
        </div>
      </Section>

      <Section title="গুরুত্বপূর্ণ প্রতিষ্ঠান ও স্থান" id="places">
        {places.items.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {places.items.map((p) => <PlaceCard key={p.public_id} place={p} />)}
          </div>
        ) : (
          <EmptyState title="এই এলাকার কোনো প্রকাশিত স্থান এখনো নেই" body="আপনি জানেন এমন কোনো স্থান যোগ করতে পারেন — যাচাইয়ের পর প্রকাশিত হবে।" />
        )}
        <Link href={`/contribute/new?type=new_place&area=${encodeURIComponent(area.path)}`} className="mt-3 inline-block text-sm font-medium text-secondary underline">
          নতুন স্থান যোগ করুন
        </Link>
      </Section>

      {area.website && (
        <a href={area.website} target="_blank" rel="noopener noreferrer" className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-secondary underline">
          অফিসিয়াল ওয়েবসাইট <ExternalLink className="h-4 w-4" aria-hidden />
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
