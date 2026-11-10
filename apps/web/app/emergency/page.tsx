import Link from 'next/link';
import type { Metadata } from 'next';
import { Flame, HeartPulse, MapPin, Phone, ShieldAlert, Siren } from 'lucide-react';
import type { EmergencyNumber } from '@elaka360/shared';
import { EVIDENCE_LABEL, toBnDigits } from '@elaka360/shared';
import { api } from '@/lib/api';
import { Card, Section } from '@/components/ui';
import fallback from '@/public/data/hotlines.json';

/**
 * Must work when the API is down (finding C2): statically rendered, revalidated hourly, and falls back to
 * the hotline list bundled at build time from the seed (only numbers with official/secondary evidence).
 */
export const revalidate = 3600;
export const metadata: Metadata = { title: 'জরুরি সেবা' };

async function hotlines(): Promise<{ items: Pick<EmergencyNumber, 'number' | 'name_bn' | 'name_en' | 'category' | 'evidence_level' | 'notes'>[]; live: boolean }> {
  try {
    return { items: await api.emergency(), live: true };
  } catch {
    return { items: fallback as EmergencyNumber[], live: false };
  }
}

const QUICK = [
  { label: 'পুলিশ', sub: '৯৯৯', tel: '999', Icon: ShieldAlert },
  { label: 'ফায়ার সার্ভিস', sub: '১০২ / ৯৯৯', tel: '102', Icon: Flame },
  { label: 'অ্যাম্বুলেন্স', sub: '৯৯৯', tel: '999', Icon: HeartPulse },
];

export default async function EmergencyPage() {
  const { items, live } = await hotlines();
  const hasFire = items.some((n) => n.number === '102');
  return (
    <>
      <section className="hero-red -mx-4 mt-0 px-4 py-6 md:mx-0 md:mt-4 md:rounded-card md:px-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Siren className="h-7 w-7" aria-hidden /> জরুরি সেবা
        </h1>
        <p className="mt-1 text-sm text-white/90">পুলিশ, ফায়ার সার্ভিস ও অ্যাম্বুলেন্সের জন্য জাতীয় জরুরি নম্বর ৯৯৯ — বিনামূল্যে, ২৪ ঘণ্টা।</p>
        <a href="tel:999" className="mt-4 flex items-center justify-between rounded-card bg-white px-4 py-4 text-[#b51d1d] shadow-card">
          <span className="flex items-center gap-2 text-lg font-semibold">
            <Phone className="h-7 w-7" aria-hidden /> ৯৯৯-এ কল করুন
          </span>
          <span className="font-en text-4xl font-bold">999</span>
        </a>
      </section>

      <div className="mt-4 grid grid-cols-3 gap-3">
        {QUICK.filter((q) => q.tel === '999' || hasFire).map(({ label, sub, tel, Icon }) => (
          <a key={label} href={`tel:${tel}`} className="flex flex-col items-center gap-1 rounded-card border border-line bg-surface p-3 text-center shadow-card">
            <Icon className="h-7 w-7 text-danger" aria-hidden />
            <span className="text-sm font-semibold">{label}</span>
            <span className="text-xs text-muted">{sub}</span>
          </a>
        ))}
      </div>

      <Link href="/near-me?category=emergency" className="mt-3 flex items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 font-semibold">
        <MapPin className="h-5 w-5 text-danger" aria-hidden /> কাছাকাছি জরুরি সেবা ও হাসপাতাল খুঁজুন
      </Link>

      <Section title="গুরুত্বপূর্ণ জাতীয় হটলাইন">
        <Card className="divide-y divide-line">
          {items.map((n) => (
            <a key={n.number} href={`tel:${n.number}`} className="flex items-center gap-3 px-4 py-3">
              <span className="w-20 text-xl font-bold text-danger">{toBnDigits(n.number)}</span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{n.name_bn}</span>
                <span className="block font-en text-xs text-muted">{n.name_en}</span>
                {n.notes && <span className="block text-[11px] text-muted">{n.notes}</span>}
              </span>
              <span className="grid h-10 w-10 place-items-center rounded-full bg-secondary text-on-primary" aria-hidden>
                <Phone className="h-5 w-5" />
              </span>
            </a>
          ))}
        </Card>
        <p className="mt-2 text-xs text-muted">
          শুধু উৎসসহ নম্বর দেখানো হয় ({EVIDENCE_LABEL.secondary.bn})। ফায়ার সার্ভিসের নতুন হটলাইন ১০২; পুরনো ১৬১৬৩ বন্ধ হয়েছে।
          {!live && ' সার্ভারের সঙ্গে সংযোগ না থাকায় সংরক্ষিত তালিকা দেখানো হচ্ছে।'}
        </p>
      </Section>
    </>
  );
}
