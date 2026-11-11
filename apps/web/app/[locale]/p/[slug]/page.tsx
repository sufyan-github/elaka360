import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Globe, Mail, MapPin, Navigation, Phone, Star } from 'lucide-react';
import { formatDate, formatNumber, type Locale } from '@elaka360/shared';
import { ApiError, api, categoryName } from '@/lib/api';
import { areaLabel, asLocale, digits, localName, otherLocale, otherName } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { categoryColor, categoryIcon } from '@/lib/icons';
import { MapView } from '@/components/map/MapView';
import { SaveShare } from '@/components/client/SaveShare';
import { ReviewForm } from '@/components/client/ReviewForm';
import { Breadcrumb, Card, Chip, EvidenceBadge, Section, SourceFooter, UnverifiedNotice } from '@/components/ui';

export const revalidate = 300;
/** Rendered on first request, then cached and revalidated (ISR). */
export async function generateStaticParams() {
  return [];
}

type Props = { params: Promise<{ locale: string; slug: string }> };

async function load(slug: string) {
  if (!/^[a-z0-9-]{1,120}$/.test(slug)) return null;
  try {
    return await api.place(slug);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 400)) return null;
    throw e;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug, locale: raw } = await params;
  const locale = asLocale(raw);
  const p = await load(slug);
  if (!p) return { title: (await getTranslations({ locale, namespace: 'Place' }))('notFound') };
  return {
    title: localName(p, locale),
    description: [otherName(p, locale), areaLabel(p, locale)].filter(Boolean).join(' · '),
    ...(p.production_eligible ? {} : { robots: { index: false, follow: true } }),
    alternates: localeAlternates(locale, `/p/${p.slug}`),
  };
}

const YEAR_KEYS = new Set(['university_status_year', 'college_established', 'hospital_opened']);

/** Numbers are grouped in the locale's digits (finding C19); years keep plain (ungrouped) digits. */
function attrValue(k: string, v: unknown, locale: Locale): string {
  if (typeof v === 'number') return YEAR_KEYS.has(k) ? digits(v, locale) : formatNumber(v, locale);
  return digits(String(v), locale);
}

export default async function PlacePage({ params }: Props) {
  const { slug, locale: raw } = await params;
  const locale = asLocale(raw);
  setRequestLocale(locale);
  const [t, tAttr] = await Promise.all([getTranslations('Place'), getTranslations('PlaceAttr')]);
  const p = await load(slug);
  if (!p) notFound();
  const [categories, reviews] = await Promise.all([api.categories(), api.reviews(slug).catch(() => ({ items: [], next_cursor: null }))]);
  const Icon = categoryIcon(p.category_key);
  const hasPoint = p.lat !== null && p.lon !== null;
  const directions = hasPoint ? `https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}` : null;
  // keys starting with `_` are internal (source ids, merge notes); only show plain values
  const attrs = Object.entries(p.attributes ?? {}).filter(
    ([k, v]) => !k.startsWith('_') && v !== null && v !== '' && ['string', 'number', 'boolean'].includes(typeof v),
  );
  const sub = categoryName(categories, p.subcategory_key, locale) ?? categoryName(categories, p.category_key, locale);
  const other = otherName(p, locale);
  const address = locale === 'en'
    ? p.address_en ?? p.address_bn ?? areaLabel(p, locale)
    : p.address_bn ?? p.address_en ?? areaLabel(p, locale);
  const description = locale === 'en' ? p.description_en ?? p.description_bn : p.description_bn ?? p.description_en;
  const attrLabel = (k: string) => (tAttr.has(k as never) ? tAttr(k as never) : k.replace(/_/g, ' '));

  return (
    <>
      <div className="pt-4">
        <Breadcrumb items={p.breadcrumb} />
      </div>
      {!p.production_eligible && <UnverifiedNotice level={p.evidence_level} reportHref={`/contribute/new?type=correction&place=${p.slug}`} />}
      <Card className="mt-3 overflow-hidden">
        <div className="hero-green flex h-28 items-end px-5 pb-3">
          <span className="grid h-16 w-16 translate-y-8 place-items-center rounded-full border-4 border-surface bg-surface">
            <Icon className="h-8 w-8" style={{ color: categoryColor(p.category_key) }} aria-hidden />
          </span>
        </div>
        <div className="px-5 pb-5 pt-10">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold">{localName(p, locale)}</h1>
            <EvidenceBadge level={p.evidence_level} />
          </div>
          {other && <p lang={otherLocale(locale)} className={`text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{other}{p.short_name ? ` (${p.short_name})` : ''}</p>}
          <div className="mt-2 flex flex-wrap gap-2">
            {sub && <Chip>{sub}</Chip>}
            {p.ownership === 'public' && <Chip tone="line">{t('public')}</Chip>}
            {p.established && <Chip tone="line">{t('established', { year: digits(p.established.slice(0, 4), locale) })}</Chip>}
            {p.rating_count > 0 && p.rating_avg !== null && (
              <Chip tone="line"><Star className="mr-1 h-3.5 w-3.5 fill-accent text-accent" aria-hidden />{digits(p.rating_avg.toFixed(1), locale)} ({formatNumber(p.rating_count, locale)})</Chip>
            )}
          </div>
          {address && (
            <p className="mt-3 flex items-start gap-1.5 text-sm">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden /> {address}
            </p>
          )}
          <div className="mt-4 grid grid-cols-4 gap-2 text-sm">
            {p.phones[0] ? (
              <a href={`tel:${p.phones[0]}`} className="flex flex-col items-center gap-1 rounded-chip bg-primary py-2 font-medium text-on-primary">
                <Phone className="h-5 w-5" aria-hidden /> {t('call')}
              </a>
            ) : (
              <span className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 text-muted" title={t('noPhone')}>
                <Phone className="h-5 w-5" aria-hidden /> {t('call')}
              </span>
            )}
            {directions ? (
              <a href={directions} target="_blank" rel="noopener noreferrer" className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 font-medium">
                <Navigation className="h-5 w-5" aria-hidden /> {t('directions')}
              </a>
            ) : (
              <span className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 text-muted">
                <Navigation className="h-5 w-5" aria-hidden /> {t('directions')}
              </span>
            )}
            <SaveShare placeSlug={p.slug} title={localName(p, locale)} />
          </div>
        </div>
      </Card>

      {description && (
        <Section title={t('description')}>
          <p className="text-[15px]">{description}</p>
        </Section>
      )}

      {attrs.length > 0 && (
        <Section title={t('keyFacts')}>
          <Card>
            <dl className="divide-y divide-line">
              {attrs.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 px-4 py-2.5 text-sm">
                  <dt className="text-muted">{attrLabel(k)}</dt>
                  <dd className="text-right font-medium">{attrValue(k, v, locale)}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </Section>
      )}

      <Section title={t('contact')}>
        <Card className="space-y-2 p-4 text-sm">
          {p.phones.map((ph) => (
            <a key={ph} href={`tel:${ph}`} className="flex items-center gap-2"><Phone className="h-4 w-4 text-secondary" aria-hidden /> {digits(ph, locale)}</a>
          ))}
          {p.email && <a href={`mailto:${p.email}`} className="flex items-center gap-2"><Mail className="h-4 w-4 text-secondary" aria-hidden /> {p.email}</a>}
          {p.website && <a href={p.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 break-all"><Globe className="h-4 w-4 text-secondary" aria-hidden /> {p.website}</a>}
          {!p.phones.length && !p.email && !p.website && <p className="text-muted">{t('contactUnverified')}</p>}
        </Card>
        {hasPoint && <MapView point={[p.lon!, p.lat!]} linkDistricts={false} className="mt-3 h-56" />}
      </Section>

      <Section title={reviews.items.length ? t('reviewsCount', { count: formatNumber(p.rating_count, locale) }) : t('reviews')} id="reviews">
        {reviews.items.length > 0 ? (
          <ul className="space-y-3">
            {reviews.items.map((r) => (
              <li key={r.id} className="rounded-card border border-line bg-surface p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{r.author_name}</span>
                  <span className="flex items-center gap-1 text-xs text-muted">
                    <Star className="h-3.5 w-3.5 fill-accent text-accent" aria-hidden /> {digits(r.rating, locale)} · {formatDate(r.created_at, locale)}
                  </span>
                </div>
                {r.body && <p className="mt-1">{r.body}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">{t('noReviews')}</p>
        )}
        <div className="mt-4 rounded-card border border-line bg-surface p-4">
          <ReviewForm slug={p.slug} />
        </div>
      </Section>

      <SourceFooter
        source={p.source}
        detailsSource={p.details_source}
        verifiedAt={p.last_verified_at}
        note={p.source_notes}
        evidence={p.evidence_level}
        reportHref={`/contribute/new?type=correction&place=${p.slug}`}
      />
      <p className="mt-2 text-xs text-muted">
        {t.rich('policyNote', { link: (c) => <Link href="/data-policy" className="underline">{c}</Link> })}
      </p>
    </>
  );
}
