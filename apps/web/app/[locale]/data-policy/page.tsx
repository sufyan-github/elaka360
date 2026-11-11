import fs from 'node:fs';
import path from 'node:path';
import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { ExternalLink } from 'lucide-react';
import type { EvidenceLevel } from '@elaka360/shared';
import { asLocale, evidenceText, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';

// Rendered once at build time (per locale) from the committed seed (data/seed/**), so names and URLs match it exactly.
export const dynamic = 'force-static';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'DataPolicy' });
  return { title: t('title'), description: t('description'), alternates: localeAlternates(locale, '/data-policy') };
}

/* ---------------------------------------------------------------- build-time seed reading */

function seedDir(): string {
  let dir = process.cwd();
  for (let i = 0; i < 5; i++) {
    const candidate = path.join(dir, 'data', 'seed');
    if (fs.existsSync(path.join(candidate, 'reference', 'data_sources.csv'))) return candidate;
    dir = path.dirname(dir);
  }
  throw new Error('data-policy: data/seed not found (looked upwards from the web app directory)');
}

/** Minimal RFC 4180 parser (quoted fields, doubled quotes, CRLF), returning objects keyed by the header row. */
function readCsv(file: string): Record<string, string>[] {
  const text = fs.readFileSync(path.join(seedDir(), file), 'utf8').replace(/^\uFEFF/, '');
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else field += c;
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [header, ...body] = rows.filter((r) => r.some((x) => x !== ''));
  return body.map((r) => Object.fromEntries(header!.map((h, i) => [h, r[i] ?? ''])));
}

type Source = { key: string; name: string; url: string };

function loadSources() {
  const all = readCsv('reference/data_sources.csv').map((r) => ({ key: r.key!, name: r.name!, url: r.url ?? '' }));
  const published = new Set<string>();
  const heldBack = new Set<string>();
  for (const a of readCsv('geo/admin_areas.csv')) {
    if (a.production_eligible === 'True') {
      if (a.evidence_source) published.add(a.evidence_source);
      if (a.population_source) published.add(a.population_source);
    } else if (a.evidence_level === 'community') heldBack.add(a.data_source || a.evidence_source || '');
  }
  for (const p of readCsv('pilot_rajshahi/places.csv')) if (p.production_eligible === 'True' && p.source) published.add(p.source);
  for (const h of readCsv('reference/emergency_hotlines.csv')) if ((h.evidence_level === 'official' || h.evidence_level === 'secondary') && h.source) published.add(h.source);

  const byKey = new Map(all.map((s) => [s.key, s]));
  const pick = (keys: Set<string>) => all.filter((s) => keys.has(s.key) && s.url) as Source[];
  const missing = [...published].filter((k) => !byKey.has(k));
  if (missing.length) throw new Error(`data-policy: published records cite unknown source keys: ${missing.join(', ')}`);
  return { published: pick(published), heldBack: pick(new Set([...heldBack].filter((k) => !published.has(k)))) };
}

/** known_gaps.csv `area` values → message keys (DataPolicy.gapArea.*). */
const GAP_AREA = {
  unions: 'unions', upazilas: 'upazilas', codes: 'codes', pourashavas: 'pourashavas', 'wards/villages': 'wardsVillages',
  area: 'area', population: 'population', places: 'places',
} as const;

/* ---------------------------------------------------------------- page */

const LEVELS: EvidenceLevel[] = ['official', 'secondary', 'community', 'unverified'];
const linkCls = 'font-medium text-secondary underline';

export default async function DataPolicyPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('DataPolicy');
  const { published, heldBack } = loadSources();
  const gaps = readCsv('qa/known_gaps.csv');
  const strong = (c: React.ReactNode) => <strong>{c}</strong>;
  const official = evidenceText('official', locale).label;
  const secondary = evidenceText('secondary', locale).label;
  const gapArea = (a: string) => (a in GAP_AREA ? t(`gapArea.${GAP_AREA[a as keyof typeof GAP_AREA]}`) : a);

  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p lang={otherLocale(locale)} className={`text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{t('subtitleOther')}</p>
      <p className="mt-3 text-[15px]">{t.rich('intro', { strong })}</p>

      <Section title={t('levelsTitle')}>
        <Card className="divide-y divide-line">
          {LEVELS.map((k) => (
            <div key={k} className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-tint px-2.5 py-0.5 text-sm font-medium text-primary">{evidenceText(k, locale).label}</span>
                <span lang={otherLocale(locale)} className={`text-xs text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{evidenceText(k, otherLocale(locale)).label}</span>
                <span className={`ml-auto text-xs font-medium ${k === 'official' || k === 'secondary' ? 'text-verified' : 'text-muted'}`}>
                  {k === 'official' || k === 'secondary' ? t('sourced') : t('shownWithWarning')}
                </span>
              </div>
              <p className="mt-1 text-sm">{evidenceText(k, locale).hint}</p>
            </div>
          ))}
        </Card>
        <p className="mt-2 text-sm text-muted">{t('verifiedWord')}</p>
      </Section>

      <Section title={t('diffTitle')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t('diffIntro')}</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>{t.rich('diffLi1', { strong, official, secondary })}</li>
            <li>{t('diffLi2')}</li>
          </ul>
          <p>{t('diffRest')}</p>
        </Card>
      </Section>

      <Section title={t('whyTitle')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t('why1')}</p>
          <p>{t('why2')}</p>
        </Card>
      </Section>

      <Section title={t('populationTitle')}>
        <Card className="p-4 text-[15px]">
          <p>{t.rich('population', { strong })}</p>
        </Card>
      </Section>

      <Section title={t('correctionsTitle')}>
        <Card className="p-4 text-[15px]">
          <ol className="list-decimal space-y-1.5 pl-5">
            <li>
              {t.rich('corrections1', {
                contact: (c) => <Link href="/contact" className={linkCls}>{c}</Link>,
                contribute: (c) => <Link href="/contribute" className={linkCls}>{c}</Link>,
              })}
            </li>
            <li>{t('corrections2')}</li>
            <li>{t('corrections3')}</li>
          </ol>
          <p className="mt-2 text-sm text-muted">
            {t.rich('correctionsMore', { link: (c) => <Link href="/guidelines" className="text-secondary underline">{c}</Link> })}
          </p>
        </Card>
      </Section>

      <Section title={t('sourcesTitle')}>
        <Card className="divide-y divide-line">
          {published.map((s) => (
            <a key={s.key} href={s.url} target="_blank" rel="noreferrer" className="flex items-start gap-2 px-4 py-2.5 hover:bg-tint">
              <span lang="en" className="min-w-0 flex-1 font-en text-sm break-words">
                {s.name}
              </span>
              <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
              <span className="sr-only">{t('newTab')}</span>
            </a>
          ))}
        </Card>
        <p className="mt-2 text-xs text-muted">{t('sourcesNote')}</p>

        {heldBack.length > 0 && (
          <>
            <h3 className="mt-4 mb-2 font-semibold">{t('heldBackTitle')}</h3>
            <Card className="divide-y divide-line">
              {heldBack.map((s) => (
                <a key={s.key} href={s.url} target="_blank" rel="noreferrer" className="flex items-start gap-2 px-4 py-2.5 hover:bg-tint">
                  <span className="min-w-0 flex-1">
                    <span lang="en" className="block font-en text-sm break-words">
                      {s.name}
                    </span>
                    <span className="block text-xs text-muted">{t('heldBackNote', { label: evidenceText('community', locale).label })}</span>
                  </span>
                  <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
                  <span className="sr-only">{t('newTab')}</span>
                </a>
              ))}
            </Card>
          </>
        )}
      </Section>

      <Section title={t('gapsTitle')}>
        <p className="mb-2 text-sm">{t('gapsIntro')}</p>
        <Card className="divide-y divide-line">
          {gaps.map((g, i) => (
            <div key={i} className="px-4 py-3">
              <span className="rounded-full border border-line px-2 py-0.5 text-xs">{gapArea(g.area ?? '')}</span>
              <p lang="en" className="mt-1.5 font-en text-sm">
                {g.gap}
              </p>
              <p lang="en" className="mt-0.5 font-en text-xs text-muted">
                <span lang={locale} className={locale === 'bn' ? 'font-bn' : ''}>
                  {t('plannedFix')}
                </span>{' '}
                {g.fix}
              </p>
            </div>
          ))}
        </Card>
      </Section>
    </div>
  );
}
