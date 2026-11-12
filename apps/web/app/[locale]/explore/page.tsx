import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { LEVEL_LABEL, formatNumber, nameOf, type AdminLevel, type AreaTreeNode } from '@elaka360/shared';
import { api } from '@/lib/api';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { AreaCard } from '@/components/cards';
import { EmptyState, Section } from '@/components/ui';

type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ level?: string; division?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Explore' });
  return { title: t('metaTitle'), alternates: localeAlternates(locale, '/explore') };
}

const TABS: AdminLevel[] = ['division', 'district', 'upazila', 'city_corporation'];

export default async function ExplorePage({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Explore');
  const sp = await searchParams;
  const level = (TABS.includes(sp.level as AdminLevel) ? sp.level : 'division') as AdminLevel;
  const tree = await api.tree(1, 3);
  const divisions = tree.children ?? [];
  // An unknown ?division= is ignored instead of silently filtering against the wrong ids (finding C19).
  const division = divisions.find((d) => String(d.id) === sp.division);

  const scope: AreaTreeNode[] = division ? [division] : divisions;
  const districts = scope.flatMap((d) => d.children ?? []);
  const items: AreaTreeNode[] =
    level === 'division' ? divisions
    : level === 'district' ? districts.filter((d) => d.level === 'district')
    : districts.flatMap((d) => d.children ?? []).filter((c) => c.level === level);
  items.sort((a, b) => a.name_en.localeCompare(b.name_en));
  const pending = level === 'upazila' ? (await api.areaStats(division?.id ?? 1)).pending_counts.upazila ?? 0 : 0;

  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <p className="text-sm text-muted">{t('subtitle')}</p>
      </div>
      <nav aria-label={t('levelsNav')} className="scrollbar-none -mx-4 mt-4 flex gap-2 overflow-x-auto px-4">
        {TABS.map((tab) => (
          <Link key={tab} href={`/explore?level=${tab}${division ? `&division=${division.id}` : ''}`} aria-current={tab === level ? 'page' : undefined}
            className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium ${tab === level ? 'bg-primary text-on-primary' : 'border border-line bg-surface'}`}>
            {locale === 'bn' ? LEVEL_LABEL[tab].bn : LEVEL_LABEL[tab].plural_en}
          </Link>
        ))}
      </nav>
      {level !== 'division' && (
        <nav aria-label={t('divisionNav')} className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
          <Link href={`/explore?level=${level}`} aria-current={!division ? 'page' : undefined} className={`whitespace-nowrap rounded-full px-3 py-1 text-xs ${!division ? 'bg-tint font-semibold text-primary' : 'border border-line'}`}>
            {t('allDivisions')}
          </Link>
          {divisions.map((d) => (
            <Link key={d.id} href={`/explore?level=${level}&division=${d.id}`} aria-current={division?.id === d.id ? 'page' : undefined}
              className={`whitespace-nowrap rounded-full px-3 py-1 text-xs ${division?.id === d.id ? 'bg-tint font-semibold text-primary' : 'border border-line'}`}>
              {nameOf(d, locale)}
            </Link>
          ))}
        </nav>
      )}
      <Section title={`${LEVEL_LABEL[level][locale === 'bn' ? 'plural_bn' : 'plural_en']} (${formatNumber(items.length, locale)})`}>
        {items.length ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {items.map((a) => <AreaCard key={a.id} area={a} />)}
          </div>
        ) : (
          <EmptyState title={t('empty')} />
        )}
        {pending > 0 && (
          <p className="mt-3 text-xs text-muted">
            {t.rich('pending', { n: pending, count: formatNumber(pending, locale), link: (c) => <Link href="/data-policy" className="underline">{c}</Link> })}
          </p>
        )}
      </Section>
    </>
  );
}
