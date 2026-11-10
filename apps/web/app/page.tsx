import Link from 'next/link';
import { connection } from 'next/server';
import { Building2, Map as MapIcon, MapPin, Phone, PlusCircle, ShieldCheck, Users } from 'lucide-react';
import { formatNumber } from '@elaka360/shared';
import { api } from '@/lib/api';
import { AreaCard, CategoryTile, PlaceCard } from '@/components/cards';
import { SearchBox } from '@/components/SearchBox';
import { MapView } from '@/components/map/MapView';
import { Section, StatTile } from '@/components/ui';

/* Rendered per request (so builds never depend on a running API); every API read below is cached for 5–60 minutes. */
export default async function HomePage() {
  await connection();
  // One tree call (divisions + their districts) instead of one detail call per division (finding C15).
  const [tree, categories, stats, national, places] = await Promise.all([
    api.tree(1, 2), api.categories(), api.nationalStats(), api.areaStats(1), api.places({ limit: 6 }),
  ]);
  const divisions = tree.children ?? [];
  const pendingUnions = national.pending_counts.union ?? 0;
  const pendingUpazilas = national.pending_counts.upazila ?? 0;

  return (
    <>
      <section className="hero-green -mx-4 px-4 pb-6 pt-8 md:mx-0 md:mt-4 md:rounded-card md:px-8">
        <h1 className="text-[28px] leading-tight font-bold md:text-4xl">
          বাংলাদেশের প্রতিটি এলাকার
          <br />
          তথ্য, <span className="text-accent">উৎসসহ এক জায়গায়</span>
        </h1>
        <p className="mt-2 max-w-xl text-[15px] text-white/90">বিভাগ, জেলা, সিটি কর্পোরেশন, প্রতিষ্ঠান, পর্যটন স্থান ও জরুরি সেবা — প্রতিটি তথ্যের উৎস দেখানো হয়।</p>
        <div className="mt-4 text-ink">
          <SearchBox />
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          {[
            { href: '/explore?level=district', label: 'জেলা', Icon: MapPin },
            { href: '/explore?level=upazila', label: 'উপজেলা', Icon: Building2 },
            { href: '/explore?level=city_corporation', label: 'সিটি কর্পোরেশন', Icon: Users },
            { href: '/near-me', label: 'আমার কাছে', Icon: MapPin },
            { href: '/map', label: 'মানচিত্র', Icon: MapIcon },
          ].map(({ href, label, Icon }) => (
            <Link key={href} href={href} className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 font-medium text-[#1f2d28]">
              <Icon className="h-4 w-4 text-[#075b3b]" aria-hidden /> {label}
            </Link>
          ))}
        </div>
      </section>

      <Link href="/emergency" className="mt-4 flex items-center justify-between rounded-card bg-danger px-4 py-3 text-on-danger shadow-card">
        <span className="flex items-center gap-2 font-semibold">
          <Phone className="h-5 w-5" aria-hidden /> জরুরি সেবা — জাতীয় জরুরি নম্বর
        </span>
        <span className="font-en text-2xl font-bold">999</span>
      </Link>

      <Section title="বাংলাদেশ ঘুরে দেখুন" action={{ href: '/explore', label: 'সব বিভাগ দেখুন' }}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {divisions.map((d) => (
            <AreaCard key={d.id} area={d} sub={`${formatNumber(d.children?.length ?? 0)} জেলা`} />
          ))}
        </div>
      </Section>

      <Section title="কী খুঁজছেন?">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
          {categories.map((c) => (
            <CategoryTile key={c.id} category={c} href={`/c/${c.key}`} />
          ))}
        </div>
      </Section>

      {places.items.length > 0 && (
        <Section title="কিছু স্থান" action={{ href: '/search?q=রাজশাহী', label: 'আরও' }}>
          <div className="grid gap-3 md:grid-cols-2">
            {places.items.map((p) => <PlaceCard key={p.public_id} place={p} />)}
          </div>
        </Section>
      )}

      <Section title="মানচিত্রে বাংলাদেশ" action={{ href: '/map', label: 'পূর্ণ মানচিত্র' }}>
        <MapView className="h-80 md:h-[28rem]" />
      </Section>

      <Link href="/contribute" className="mt-6 flex items-center gap-3 rounded-card border border-line bg-surface p-4 shadow-card hover:border-secondary">
        <PlusCircle className="h-8 w-8 shrink-0 text-secondary" aria-hidden />
        <span>
          <span className="block font-semibold">আপনার এলাকার তথ্য যোগ করুন</span>
          <span className="block text-sm text-muted">নতুন স্থান বা ভুল সংশোধন প্রস্তাব করুন — যাচাইয়ের পর প্রকাশিত হবে।</span>
        </span>
      </Link>

      <Section title="Elaka360-এ যা আছে">
        <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
          {([
            ['বিভাগ', stats.division, stats.sourced.division],
            ['জেলা', stats.district, stats.sourced.district],
            ['উপজেলা', stats.upazila, stats.sourced.upazila],
            ['ইউনিয়ন', stats.union, stats.sourced.union],
            ['সিটি কর্পোরেশন', stats.city_corporation, stats.sourced.city_corporation],
            ['স্থান', stats.places, stats.sourced.places],
          ] as const).map(([label, total, sourced]) => (
            <StatTile key={label} label={label} value={formatNumber(total)}
              sub={sourced < total ? `উৎসসহ ${formatNumber(sourced)}` : 'সবগুলো উৎসসহ'} />
          ))}
        </div>
        {(pendingUnions > 0 || pendingUpazilas > 0) && (
          <p className="mt-2 text-xs text-muted">আরও {formatNumber(pendingUnions + pendingUpazilas)}টি এলাকা যাচাইয়ের অপেক্ষায় আছে।</p>
        )}
        <p className="mt-3 flex items-start gap-2 text-xs text-muted">
          <ShieldCheck className="h-4 w-4 shrink-0 text-secondary" aria-hidden />
          <span>
            সংখ্যাগুলো সরাসরি ডেটাবেস থেকে আসে। “উৎসসহ” মানে উইকিপিডিয়া, আদমশুমারি বা সংবাদপত্রের মতো উৎসের সঙ্গে মেলানো; বাকিগুলো যাচাই হয়নি এবং পাতায় তা লেখা থাকে। উৎস: উইকিপিডিয়া, BBS জনশুমারি ২০২২ (citypopulation.de-এর সংকলন),
            The Financial Express; প্রশাসনিক কাঠামোর কমিউনিটি ডেটাসেট (nuhil/bangladesh-geocode) যাচাইয়ের অপেক্ষায়।{' '}
            <Link href="/data-policy" className="text-secondary underline">তথ্য ও যাচাই নীতি</Link>
          </span>
        </p>
      </Section>
    </>
  );
}
