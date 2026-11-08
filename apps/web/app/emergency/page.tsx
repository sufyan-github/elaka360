import Link from 'next/link';
import type { Metadata } from 'next';
import { MapPin, Phone, Siren } from 'lucide-react';
import { toBnDigits } from '@elaka360/shared';
import { api } from '@/lib/api';
import { Card, Section } from '@/components/ui';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'জরুরি সেবা' };

export default async function EmergencyPage() {
  const numbers = await api.emergency();
  return (
    <>
      <section className="hero-red -mx-4 mt-0 px-4 py-6 text-white md:mx-0 md:mt-4 md:rounded-card md:px-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Siren className="h-7 w-7" /> জরুরি সেবা
        </h1>
        <p className="mt-1 text-sm text-white/90">দ্রুত সহায়তা, নির্ভরযোগ্য তথ্য এবং নিকটস্থ জরুরি সেবা — একসাথে।</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <a href="tel:999" className="flex items-center justify-between rounded-card bg-white px-4 py-3 text-danger shadow-card">
            <span className="flex items-center gap-2 font-semibold">
              <Phone className="h-6 w-6" /> জরুরি কল করুন
            </span>
            <span className="font-en text-3xl font-bold">999</span>
          </a>
          <Link href="/near-me?category=emergency" className="flex items-center gap-2 rounded-card bg-white/15 px-4 py-3 font-semibold">
            <MapPin className="h-5 w-5" /> কাছাকাছি জরুরি সেবা খুঁজুন
          </Link>
        </div>
      </section>

      <Section title="গুরুত্বপূর্ণ জরুরি নম্বরসমূহ">
        <Card className="divide-y divide-line">
          {numbers.map((n) => (
            <a key={n.number} href={`tel:${n.number}`} className="flex items-center gap-3 px-4 py-3">
              <span className="w-20 text-xl font-bold text-danger">{toBnDigits(n.number)}</span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{n.name_bn}</span>
                <span className="block font-en text-xs text-muted">{n.name_en}</span>
                {!n.verified && <span className="text-[11px] text-muted">যাচাই প্রক্রিয়াধীন</span>}
              </span>
              <span className="grid h-10 w-10 place-items-center rounded-full bg-secondary text-white">
                <Phone className="h-5 w-5" />
              </span>
            </a>
          ))}
        </Card>
        <p className="mt-2 text-xs text-muted">ফায়ার সার্ভিসের নতুন হটলাইন ১০২ (পুরনো ১৬১৬৩ বন্ধ)।</p>
      </Section>
    </>
  );
}
