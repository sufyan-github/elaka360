import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { Globe, Mail, MapPin, Navigation, Phone } from 'lucide-react';
import { formatDate, toBnDigits } from '@elaka360/shared';
import { ApiError, api } from '@/lib/api';
import { categoryColor, categoryIcon } from '@/lib/icons';
import { Breadcrumb, Card, Chip, Section, SourceFooter, VerifiedBadge } from '@/components/ui';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ slug: string }> };

async function load(slug: string) {
  try {
    return await api.place(slug);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
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

export default async function PlacePage({ params }: Props) {
  const p = await load((await params).slug);
  if (!p) notFound();
  const Icon = categoryIcon(p.category_key);
  const directions = p.lat !== null && p.lon !== null ? `https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}` : null;
  const attrs = Object.entries(p.attributes ?? {}).filter(([, v]) => v !== null && v !== '');

  return (
    <>
      <div className="pt-4">
        <Breadcrumb items={p.breadcrumb} />
      </div>
      <Card className="mt-3 overflow-hidden">
        <div className="hero-green flex h-28 items-end px-5 pb-3">
          <span className="grid h-16 w-16 translate-y-8 place-items-center rounded-full border-4 border-surface bg-surface">
            <Icon className="h-8 w-8" style={{ color: categoryColor(p.category_key) }} />
          </span>
        </div>
        <div className="px-5 pb-5 pt-10">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold">{p.name_bn}</h1>
            {p.verification_status === 'verified' && <VerifiedBadge />}
          </div>
          {p.name_en && <p className="font-en text-sm text-muted">{p.name_en}{p.short_name ? ` (${p.short_name})` : ''}</p>}
          <div className="mt-2 flex flex-wrap gap-2">
            {p.subcategory_key && <Chip>{p.subcategory_key.split('.').pop()?.replace(/_/g, ' ')}</Chip>}
            {p.ownership === 'public' && <Chip tone="line">সরকারি</Chip>}
            {p.established && <Chip tone="line">স্থাপিত: {toBnDigits(p.established.slice(0, 4))}</Chip>}
          </div>
          {(p.address_bn || p.address_en || p.area_label_bn) && (
            <p className="mt-3 flex items-start gap-1.5 text-sm">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-secondary" /> {p.address_bn ?? p.address_en ?? p.area_label_bn}
            </p>
          )}
          <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
            <a href={p.phones[0] ? `tel:${p.phones[0]}` : undefined} aria-disabled={!p.phones[0]} className={`flex flex-col items-center gap-1 rounded-chip py-2 font-medium ${p.phones[0] ? 'bg-primary text-white' : 'border border-line text-muted'}`}>
              <Phone className="h-5 w-5" /> কল
            </a>
            <a href={directions ?? undefined} target="_blank" rel="noreferrer" aria-disabled={!directions} className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 font-medium">
              <Navigation className="h-5 w-5" /> দিকনির্দেশনা
            </a>
            <a href={p.website ?? undefined} target="_blank" rel="noreferrer" aria-disabled={!p.website} className="flex flex-col items-center gap-1 rounded-chip border border-line py-2 font-medium">
              <Globe className="h-5 w-5" /> ওয়েবসাইট
            </a>
          </div>
        </div>
      </Card>

      {attrs.length > 0 && (
        <Section title="গুরুত্বপূর্ণ তথ্য">
          <Card>
            <dl className="divide-y divide-line">
              {attrs.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 px-4 py-2.5 text-sm">
                  <dt className="text-muted">{ATTR_LABEL[k] ?? k.replace(/_/g, ' ')}</dt>
                  <dd className="text-right font-medium">{typeof v === 'number' ? toBnDigits(v) : toBnDigits(String(v))}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </Section>
      )}

      <Section title="যোগাযোগ ও অবস্থান">
        <Card className="space-y-2 p-4 text-sm">
          {p.phones.map((ph) => (
            <a key={ph} href={`tel:${ph}`} className="flex items-center gap-2"><Phone className="h-4 w-4 text-secondary" /> {ph}</a>
          ))}
          {p.email && <a href={`mailto:${p.email}`} className="flex items-center gap-2"><Mail className="h-4 w-4 text-secondary" /> {p.email}</a>}
          {p.website && <a href={p.website} target="_blank" rel="noreferrer" className="flex items-center gap-2 break-all"><Globe className="h-4 w-4 text-secondary" /> {p.website}</a>}
          {p.lat !== null && p.lon !== null && (
            <p className="flex items-center gap-2 font-en text-muted"><MapPin className="h-4 w-4 text-secondary" /> {p.lat.toFixed(4)}° N, {p.lon.toFixed(4)}° E</p>
          )}
          {!p.phones.length && !p.email && !p.website && p.lat === null && <p className="text-muted">যোগাযোগের তথ্য এখনো যাচাই হয়নি।</p>}
        </Card>
      </Section>

      <SourceFooter source={p.source} verifiedAt={p.last_verified_at} note={p.source_notes} />
      {p.last_verified_at && <p className="mt-2 text-right text-[11px] text-muted">হালনাগাদ: {formatDate(p.last_verified_at)}</p>}
    </>
  );
}
