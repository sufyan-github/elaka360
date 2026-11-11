import type { Metadata } from 'next';
import { connection } from 'next/server';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Building2, Map as MapIcon, MapPin, Phone, PlusCircle, ShieldCheck, Users } from 'lucide-react';
import { LEVEL_LABEL, formatNumber } from '@elaka360/shared';
import { api } from '@/lib/api';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { AreaCard, CategoryTile, PlaceCard } from '@/components/cards';
import { SearchBox } from '@/components/SearchBox';
import { MapView } from '@/components/map/MapView';
import { Section, StatTile } from '@/components/ui';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { alternates: localeAlternates(asLocale((await params).locale), '/') };
}

/* Rendered per request (so builds never depend on a running API); every API read below is cached for 5–60 minutes. */
export default async function HomePage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  await connection();
  const t = await getTranslations('Home');
  // One tree call (divisions + their districts) instead of one detail call per division (finding C15).
  const [tree, categories, stats, national, places] = await Promise.all([
    api.tree(1, 2), api.categories(), api.nationalStats(), api.areaStats(1), api.places({ limit: 6 }),
  ]);
  const divisions = tree.children ?? [];
  const pendingUnions = national.pending_counts.union ?? 0;
  const pendingUpazilas = national.pending_counts.upazila ?? 0;
  const level = (l: keyof typeof LEVEL_LABEL) => (locale === 'bn' ? LEVEL_LABEL[l].bn : LEVEL_LABEL[l].plural_en);
  const num = (n: number) => formatNumber(n, locale);

  return (
    <>
      <section className="hero-green -mx-4 px-4 pb-6 pt-8 md:mx-0 md:mt-4 md:rounded-card md:px-8">
        <h1 className="text-[28px] leading-tight font-bold md:text-4xl">
          {t.rich('heroTitle', { br: () => <br />, accent: (c) => <span className="text-accent">{c}</span> })}
        </h1>
        <p className="mt-2 max-w-xl text-[15px] text-white/90">{t('heroSub')}</p>
        <div className="mt-4 text-ink">
          <SearchBox />
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          {[
            { href: '/explore?level=district', label: level('district'), Icon: MapPin },
            { href: '/explore?level=upazila', label: level('upazila'), Icon: Building2 },
            { href: '/explore?level=city_corporation', label: level('city_corporation'), Icon: Users },
            { href: '/near-me', label: t('nearMe'), Icon: MapPin },
            { href: '/map', label: t('map'), Icon: MapIcon },
          ].map(({ href, label, Icon }) => (
            <Link key={href} href={href} className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 font-medium text-[#1f2d28]">
              <Icon className="h-4 w-4 text-[#075b3b]" aria-hidden /> {label}
            </Link>
          ))}
        </div>
      </section>

      <Link href="/emergency" className="mt-4 flex items-center justify-between rounded-card bg-danger px-4 py-3 text-on-danger shadow-card">
        <span className="flex items-center gap-2 font-semibold">
          <Phone className="h-5 w-5" aria-hidden /> {t('emergency')}
        </span>
        <span className="font-en text-2xl font-bold">999</span>
      </Link>

      <Section title={t('exploreTitle')} action={{ href: '/explore', label: t('exploreAll') }}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {divisions.map((d) => {
            const n = d.children?.length ?? 0;
            return <AreaCard key={d.id} area={d} sub={t('districtCount', { n, count: num(n) })} />;
          })}
        </div>
      </Section>

      <Section title={t('lookingFor')}>
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
          {categories.map((c) => (
            <CategoryTile key={c.id} category={c} href={`/c/${c.key}`} />
          ))}
        </div>
      </Section>

      {places.items.length > 0 && (
        <Section title={t('somePlaces')} action={{ href: `/search?q=${encodeURIComponent(t('moreQuery'))}`, label: t('more') }}>
          <div className="grid gap-3 md:grid-cols-2">
            {places.items.map((p) => <PlaceCard key={p.public_id} place={p} />)}
          </div>
        </Section>
      )}

      <Section title={t('mapTitle')} action={{ href: '/map', label: t('fullMap') }}>
        <MapView className="h-80 md:h-[28rem]" />
      </Section>

      <Link href="/contribute" className="mt-6 flex items-center gap-3 rounded-card border border-line bg-surface p-4 shadow-card hover:border-secondary">
        <PlusCircle className="h-8 w-8 shrink-0 text-secondary" aria-hidden />
        <span>
          <span className="block font-semibold">{t('contributeTitle')}</span>
          <span className="block text-sm text-muted">{t('contributeBody')}</span>
        </span>
      </Link>

      <Section title={t('statsTitle')}>
        <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
          {([
            [level('division'), stats.division, stats.sourced.division],
            [level('district'), stats.district, stats.sourced.district],
            [level('upazila'), stats.upazila, stats.sourced.upazila],
            [level('union'), stats.union, stats.sourced.union],
            [level('city_corporation'), stats.city_corporation, stats.sourced.city_corporation],
            [t('places'), stats.places, stats.sourced.places],
          ] as const).map(([label, total, sourced]) => (
            <StatTile key={label} label={label} value={num(total)}
              sub={sourced < total ? t('sourcedCount', { count: num(sourced) }) : t('allSourced')} />
          ))}
        </div>
        {(pendingUnions > 0 || pendingUpazilas > 0) && (
          <p className="mt-2 text-xs text-muted">{t('pending', { n: pendingUnions + pendingUpazilas, count: num(pendingUnions + pendingUpazilas) })}</p>
        )}
        <p className="mt-3 flex items-start gap-2 text-xs text-muted">
          <ShieldCheck className="h-4 w-4 shrink-0 text-secondary" aria-hidden />
          <span>
            {t.rich('sourcesNote', {
              link: (c) => <Link href="/data-policy" className="text-secondary underline">{c}</Link>,
            })}
          </span>
        </p>
      </Section>
    </>
  );
}
