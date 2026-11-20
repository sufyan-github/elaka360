import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { ArrowLeft } from 'lucide-react';
import { formatNumber, nameOf, titleOf, type CoverageRow, type CoverageService, type Locale } from '@elaka360/shared';
import { ApiError, api } from '@/lib/api';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section, StatTile } from '@/components/ui';

export const revalidate = 3600;

type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ area?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Coverage' });
  return { title: t('title'), description: t('description'), alternates: localeAlternates(locale, '/coverage') };
}

/** Child levels that have a coverage report of their own (drill down); others link to the area page. */
const DRILL = new Set(['division', 'district', 'upazila']);

const pct = (n: number, of: number, locale: Locale) => (of ? `${formatNumber(Math.round((100 * n) / of), locale)}%` : '—');
const per10k = (r: CoverageRow) => (r.area.population_2022 ? (10_000 * r.places) / r.area.population_2022 : null);

export default async function CoveragePage({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Coverage');
  const raw = (await searchParams).area;
  const id = raw && /^\d{1,9}$/.test(raw) ? Number(raw) : 1;
  let report;
  try {
    report = await api.coverage(id);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 400)) notFound();
    throw e;
  }
  const { area: total, rows, unfiled, services } = report;
  const a = total.area;
  const n = (v: number) => formatNumber(v, locale);
  const svc = (k: CoverageService) => t(`service.${k}`);
  // lowest coverage first: places per 10,000 people (areas without a population figure last)
  const sorted = [...rows].sort((x, y) => (per10k(x) ?? Infinity) - (per10k(y) ?? Infinity) || x.places - y.places);
  const childIsUnion = rows.some((r) => r.area.level === 'union');

  return (
    <div className="pt-6">
      {a.level !== 'country' && (
        <Link href={a.parent_id && a.parent_id !== 1 ? `/coverage?area=${a.parent_id}` : '/coverage'} className="mb-2 inline-flex items-center gap-1 text-sm font-medium text-secondary">
          <ArrowLeft className="h-4 w-4" aria-hidden /> {t('up')}
        </Link>
      )}
      <h1 className="text-2xl font-bold">{a.level === 'country' ? t('title') : t('titleOf', { area: titleOf(a, locale) })}</h1>
      <p className="mt-2 text-[15px]">{t('intro')}</p>
      <p className="mt-1 text-xs text-muted">{t('caveat')}</p>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
        <StatTile label={t('places')} value={n(total.places)} />
        <StatTile label={t('official')} value={pct(total.official, total.places, locale)} sub={n(total.official)} />
        <StatTile label={t('withPoint')} value={pct(total.with_point, total.places, locale)} />
        <StatTile label={t('withContact')} value={pct(total.with_contact, total.places, locale)} />
        <StatTile label={t('withNameBn')} value={pct(total.with_name_bn, total.places, locale)} />
        <StatTile label={t('unionsWithPlaces')} value={pct(total.unions_with_places, total.unions, locale)} sub={`${n(total.unions_with_places)} / ${n(total.unions)}`} />
      </div>
      {(total.villages > 0 || unfiled > 0) && (
        <p className="mt-2 text-xs text-muted">
          {total.villages > 0 && t('units', { mouzas: n(total.mouzas), villages: n(total.villages) })}{' '}
          {unfiled > 0 && t('unfiled', { n: n(unfiled) })}
        </p>
      )}

      <Section title={t('servicesTitle')}>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {services.map((k) => <StatTile key={k} label={svc(k)} value={n(total.services[k])} />)}
        </div>
      </Section>

      <Section title={t('rowsTitle')}>
        <p className="mb-2 text-xs text-muted">{t('rowsNote')}</p>
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted">
              <tr className="border-b border-line">
                <th className="px-3 py-2 font-medium">{t('colArea')}</th>
                <th className="px-3 py-2 text-right font-medium">{t('places')}</th>
                <th className="px-3 py-2 text-right font-medium">{t('colPer10k')}</th>
                <th className="px-3 py-2 text-right font-medium">{t('official')}</th>
                <th className="px-3 py-2 text-right font-medium">{t('withPoint')}</th>
                <th className="px-3 py-2 text-right font-medium">{t('withContact')}</th>
                {!childIsUnion && <th className="px-3 py-2 font-medium">{t('colMissing')}</th>}
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => {
                const d = per10k(r);
                return (
                  <tr key={r.area.id} className="border-b border-line last:border-0 align-top">
                    <td className="px-3 py-2">
                      <Link href={DRILL.has(r.area.level) ? `/coverage?area=${r.area.id}` : `/${r.area.path}`} className="font-medium text-secondary underline">
                        {nameOf(r.area, locale)}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{n(r.places)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{d === null ? '—' : formatNumber(Math.round(d * 10) / 10, locale)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{pct(r.official, r.places, locale)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{pct(r.with_point, r.places, locale)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{pct(r.with_contact, r.places, locale)}</td>
                    {!childIsUnion && (
                      <td className={`px-3 py-2 text-xs ${r.missing.length ? 'text-danger' : 'text-muted'}`}>
                        {r.missing.length ? r.missing.map(svc).join(locale === 'bn' ? ', ' : ', ') : t('noneMissing')}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      </Section>
      <p className="mt-4 text-xs text-muted">{report.inclusion_rule}</p>
    </div>
  );
}
