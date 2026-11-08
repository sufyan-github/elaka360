import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { ExternalLink, MapPin } from 'lucide-react';
import {
  CHILD_LEVELS, LEVEL_LABEL, formatArea, formatCompact, formatCount, formatNumber, nameOf, titleOf, type AdminLevel,
} from '@elaka360/shared';
import { ApiError, api } from '@/lib/api';
import { AreaCard, CategoryTile, PlaceCard } from '@/components/cards';
import { Breadcrumb, EmptyState, Section, SourceFooter, StatTile, VerifiedBadge } from '@/components/ui';

export const dynamic = 'force-dynamic';

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
    description: `${titleOf(d.area, 'bn')}${parent && parent.level !== 'country' ? `, ${nameOf(parent, 'bn')}` : ''} — প্রশাসনিক তথ্য, প্রতিষ্ঠান, সেবা ও দর্শনীয় স্থান।`,
  };
}

export default async function AreaPage({ params }: Props) {
  const d = await load((await params).path);
  if (!d) notFound();
  const { area, breadcrumb, children, descendant_counts, place_counts } = d;
  const [categories, places] = await Promise.all([api.categories(), api.places({ areaId: area.id, limit: 12 })]);
  const parent = breadcrumb.at(-2);
  const childLevels = (CHILD_LEVELS[area.level] ?? []).filter((l) => children.some((c) => c.level === l));

  const stats: { label: string; value: string; sub?: string }[] = [];
  if (area.area_km2) stats.push({ label: 'আয়তন', value: formatArea(area.area_km2), sub: area.area_basis === 'computed_from_polygon' ? 'আনুমানিক' : undefined });
  if (area.population_2022) stats.push({ label: 'জনসংখ্যা', value: formatCompact(area.population_2022), sub: `জনশুমারি ২০২২${area.population_basis === 'adjusted' ? ' (সমন্বিত)' : ''}` });
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
      <section className="hero-green mt-3 rounded-card px-5 py-6 text-white">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold md:text-3xl">{titleOf(area, 'bn')}</h1>
          {area.verified && (
            <span className="rounded-full bg-white px-2 py-0.5">
              <VerifiedBadge />
            </span>
          )}
        </div>
        <p className="font-en text-sm text-white/80">{titleOf(area, 'en')}</p>
        {parent && parent.level !== 'country' && (
          <p className="mt-2 flex items-center gap-1 text-sm text-white/90">
            <MapPin className="h-4 w-4" /> {breadcrumb.slice(1, -1).reverse().map((b) => titleOf(b, 'bn')).join(', ')}
          </p>
        )}
      </section>

      {stats.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {stats.map((s) => (
            <StatTile key={s.label} {...s} />
          ))}
        </div>
      )}

      {childLevels.map((lvl) => {
        const list = children.filter((c) => c.level === lvl);
        return (
          <Section key={lvl} id={lvl} title={`${LEVEL_LABEL[lvl].plural_bn} (${formatNumber(list.length)})`}>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {list.map((c) => (
                <AreaCard key={c.id} area={c} />
              ))}
            </div>
          </Section>
        );
      })}

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
            {places.items.map((p) => (
              <PlaceCard key={p.public_id} place={p} />
            ))}
          </div>
        ) : (
          <EmptyState title="এই এলাকার কোনো প্রতিষ্ঠান এখনো যুক্ত হয়নি" body="আপনার এলাকার তথ্য যুক্ত করার সুবিধা শীঘ্রই আসছে।" />
        )}
      </Section>

      {area.website && (
        <a href={area.website} target="_blank" rel="noreferrer" className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-secondary underline">
          অফিসিয়াল ওয়েবসাইট <ExternalLink className="h-4 w-4" />
        </a>
      )}
      <SourceFooter source={area.source} note={area.notes} />
    </>
  );
}
