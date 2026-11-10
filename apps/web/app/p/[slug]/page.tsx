import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { Globe, Mail, MapPin, Navigation, Phone, Star } from 'lucide-react';
import { formatDate, formatNumber, toBnDigits } from '@elaka360/shared';
import { ApiError, api, categoryName } from '@/lib/api';
import { categoryColor, categoryIcon } from '@/lib/icons';
import { MapView } from '@/components/map/MapView';
import { SaveShare } from '@/components/client/SaveShare';
import { ReviewForm } from '@/components/client/ReviewForm';
import { Breadcrumb, Card, Chip, EvidenceBadge, Section, SourceFooter } from '@/components/ui';

export const revalidate = 300;
/** Rendered on first request, then cached and revalidated (ISR). */
export async function generateStaticParams() {
  return [];
}

type Props = { params: Promise<{ slug: string }> };

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
  const p = await load((await params).slug);
  return p ? { title: p.name_bn, description: [p.name_en, p.area_label_bn].filter(Boolean).join(' · ') } : { title: 'পাওয়া যায়নি' };
}

const ATTR_LABEL: Record<string, string> = {
  faculties: 'অনুষদ', departments: 'বিভাগ', institutes: 'ইনস্টিটিউট', residential_halls: 'আবাসিক হল', students: 'শিক্ষার্থী',
  academic_staff: 'শিক্ষক', campus_acres: 'ক্যাম্পাস (একর)', vice_chancellor: 'উপাচার্য', university_status_year: 'বিশ্ববিদ্যালয় হিসেবে',
  college_established: 'কলেজ প্রতিষ্ঠা', hospital_opened: 'হাসপাতাল চালু', beds_history: 'শয্যা', emergency: 'জরুরি সেবা',
  built_by: 'নির্মাতা', style: 'স্থাপত্যশৈলী', distance_from_rajshahi_km: 'রাজশাহী থেকে দূরত্ব (কিমি)', complex: 'কমপ্লেক্স',
  managed_by: 'পরিচালনা', founded_by: 'প্রতিষ্ঠাতা',
};
const YEAR_KEYS = new Set(['university_status_year', 'college_established', 'hospital_opened']);

/** Numbers get Bangla digits with grouping (finding C19); years keep plain digits. */
function attrValue(k: string, v: unknown): string {
  if (typeof v === 'number') return YEAR_KEYS.has(k) ? toBnDigits(v) : formatNumber(v);
  return toBnDigits(String(v));
}

export default async function PlacePage({ params }: Props) {
  const slug = (await params).slug;
  const p = await load(slug);
  if (!p) notFound();
  const [categories, reviews] = await Promise.all([api.categories(), api.reviews(slug).catch(() => ({ items: [], next_cursor: null }))]);
  const Icon = categoryIcon(p.category_key);
  const hasPoint = p.lat !== null && p.lon !== null;
  const directions = hasPoint ? `https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}` : null;
  const attrs = Object.entries(p.attributes ?? {}).filter(([, v]) => v !== null && v !== '');
  const sub = categoryName(categories, p.subcategory_key) ?? categoryName(categories, p.category_key);

  return (
    <>
      <div className="pt-4">
        <Breadcrumb items={p.breadcrumb} />
      </div>
      <Card className="mt-3 overflow-hidden">
        <div className="hero-green flex h-28 items-end px-5 pb-3">
          <span className="grid h-16 w-16 translate-y-8 place-items-center rounded-full border-4 border-surface bg-surface">
            <Icon className="h-8 w-8" style={{ color: categoryColor(p.category_key) }} aria-hidden />
          </span>
        </div>
        <div className="px-5 pb-5 pt-10">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold">{p.name_bn}</h1>
            <EvidenceBadge level={p.evidence_level} />
          </div>
          {p.name_en && <p className="font-en text-sm text-muted">{p.name_en}{p.short_name ? ` (${p.short_name})` : ''}</p>}
          <div className="mt-2 flex flex-wrap gap-2">
            {sub && <Chip>{sub}</Chip>}
            {p.ownership === 'public' && <Chip tone="line">সরকারি</Chip>}
            {p.established && <Chip tone="line">স্থাপিত: {toBnDigits(p.established.slice(0, 4))}</Chip>}
            {p.rating_count > 0 && p.rating_avg !== null && (
              <Chip tone="line"><Star className="mr-1 h-3.5 w-3.5 fill-accent text-accent" aria-hidden />{toBnDigits(p.rating_avg.toFixed(1))} ({formatNumber(p.rating_count)})</Chip>
            )}
          </div>
          {(p.address_bn || p.address_en || p.area_label_bn) && (
            <p className="mt-3 flex items-start gap-1.5 text-sm">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden /> {p.address_bn ?? p.address_en ?? p.area_label_bn}
            </p>
          )}
          <div className="mt-4 grid grid-cols-4 gap-2 text-sm">
            {p.phones[0] ? (
              <a href={`tel:${p.phones[0]}`} className="flex flex-col items-center gap-1 rounded-chip bg-primary py-2 font-medium text-on-primary">
                <Phone className="h-5 w-5" aria-hidden /> কল
              </a>
            ) : (
              <span className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 text-muted" title="যাচাইকৃত ফোন নম্বর নেই">
                <Phone className="h-5 w-5" aria-hidden /> কল
              </span>
            )}
            {directions ? (
              <a href={directions} target="_blank" rel="noopener noreferrer" className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 font-medium">
                <Navigation className="h-5 w-5" aria-hidden /> দিকনির্দেশনা
              </a>
            ) : (
              <span className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 text-muted">
                <Navigation className="h-5 w-5" aria-hidden /> দিকনির্দেশনা
              </span>
            )}
            <SaveShare placeSlug={p.slug} title={p.name_bn} />
          </div>
        </div>
      </Card>

      {(p.description_bn || p.description_en) && (
        <Section title="বিবরণ">
          <p className="text-[15px]">{p.description_bn ?? p.description_en}</p>
        </Section>
      )}

      {attrs.length > 0 && (
        <Section title="গুরুত্বপূর্ণ তথ্য">
          <Card>
            <dl className="divide-y divide-line">
              {attrs.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 px-4 py-2.5 text-sm">
                  <dt className="text-muted">{ATTR_LABEL[k] ?? k.replace(/_/g, ' ')}</dt>
                  <dd className="text-right font-medium">{attrValue(k, v)}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </Section>
      )}

      <Section title="যোগাযোগ ও অবস্থান">
        <Card className="space-y-2 p-4 text-sm">
          {p.phones.map((ph) => (
            <a key={ph} href={`tel:${ph}`} className="flex items-center gap-2"><Phone className="h-4 w-4 text-secondary" aria-hidden /> {toBnDigits(ph)}</a>
          ))}
          {p.email && <a href={`mailto:${p.email}`} className="flex items-center gap-2"><Mail className="h-4 w-4 text-secondary" aria-hidden /> {p.email}</a>}
          {p.website && <a href={p.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 break-all"><Globe className="h-4 w-4 text-secondary" aria-hidden /> {p.website}</a>}
          {!p.phones.length && !p.email && !p.website && <p className="text-muted">যোগাযোগের তথ্য এখনো যাচাই হয়নি।</p>}
        </Card>
        {hasPoint && <MapView point={[p.lon!, p.lat!]} linkDistricts={false} className="mt-3 h-56" />}
      </Section>

      <Section title={`রিভিউ${reviews.items.length ? ` (${formatNumber(p.rating_count)})` : ''}`} id="reviews">
        {reviews.items.length > 0 ? (
          <ul className="space-y-3">
            {reviews.items.map((r) => (
              <li key={r.id} className="rounded-card border border-line bg-surface p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{r.author_name}</span>
                  <span className="flex items-center gap-1 text-xs text-muted">
                    <Star className="h-3.5 w-3.5 fill-accent text-accent" aria-hidden /> {toBnDigits(r.rating)} · {formatDate(r.created_at)}
                  </span>
                </div>
                {r.body && <p className="mt-1">{r.body}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">এখনো কোনো রিভিউ নেই।</p>
        )}
        <div className="mt-4 rounded-card border border-line bg-surface p-4">
          <ReviewForm slug={p.slug} />
        </div>
      </Section>

      <SourceFooter
        source={p.source}
        verifiedAt={p.last_verified_at}
        note={p.source_notes}
        evidence={p.evidence_level}
        reportHref={`/contribute/new?type=correction&place=${p.slug}`}
      />
      <p className="mt-2 text-xs text-muted">
        <Link href="/data-policy" className="underline">যাচাই নীতি</Link> অনুযায়ী শুধু উৎসসহ তথ্য প্রকাশিত হয়।
      </p>
    </>
  );
}
