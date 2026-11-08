import Link from 'next/link';
import { Building2, MapPin, Phone, ShieldCheck, Users } from 'lucide-react';
import { formatNumber } from '@elaka360/shared';
import { api } from '@/lib/api';
import { AreaCard, CategoryTile } from '@/components/cards';
import { SearchBox } from '@/components/SearchBox';
import { Section, StatTile } from '@/components/ui';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const [divisions, categories, stats] = await Promise.all([api.areas('division'), api.categories(), api.nationalStats()]);
  const districtCounts = await Promise.all(divisions.items.map((d) => api.areaByPath(d.path).then((x) => x.descendant_counts.district ?? 0)));

  return (
    <>
      <section className="hero-green -mx-4 px-4 pb-6 pt-8 text-white md:mx-0 md:mt-4 md:rounded-card md:px-8">
        <h1 className="text-[28px] leading-tight font-bold md:text-4xl">
          বাংলাদেশের প্রতিটি এলাকার
          <br />
          সব তথ্য, <span className="text-accent">এক জায়গায়</span>
        </h1>
        <p className="mt-2 max-w-xl text-[15px] text-white/90">জেলা, উপজেলা, ইউনিয়ন, প্রতিষ্ঠান, সেবা, ব্যবসা, পর্যটন স্থান ও আরও অনেক কিছু খুঁজে পান সহজেই।</p>
        <div className="mt-4 text-ink">
          <SearchBox />
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          {[
            { href: '/explore?level=district', label: 'জেলা', Icon: MapPin },
            { href: '/explore?level=upazila', label: 'উপজেলা', Icon: Building2 },
            { href: '/explore?level=city_corporation', label: 'সিটি কর্পোরেশন', Icon: Users },
            { href: '/near-me', label: 'আমার কাছে', Icon: MapPin },
          ].map(({ href, label, Icon }) => (
            <Link key={href} href={href} className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 font-medium text-ink">
              <Icon className="h-4 w-4 text-primary" /> {label}
            </Link>
          ))}
        </div>
      </section>

      <Link href="/emergency" className="mt-4 flex items-center justify-between rounded-card bg-danger px-4 py-3 text-white shadow-card">
        <span className="flex items-center gap-2 font-semibold">
          <Phone className="h-5 w-5" /> জরুরি সেবা — জাতীয় জরুরি নম্বর
        </span>
        <span className="font-en text-2xl font-bold">999</span>
      </Link>

      <Section title="বাংলাদেশ ঘুরে দেখুন" action={{ href: '/explore', label: 'সব বিভাগ দেখুন' }}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {divisions.items.map((d, i) => (
            <AreaCard key={d.id} area={d} sub={`${formatNumber(districtCounts[i] ?? 0)} জেলা`} />
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

      <Section title="Elaka360 সম্পর্কে">
        <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
          <StatTile label="বিভাগ" value={formatNumber(stats.division)} />
          <StatTile label="জেলা" value={formatNumber(stats.district)} />
          <StatTile label="উপজেলা" value={formatNumber(stats.upazila)} />
          <StatTile label="ইউনিয়ন" value={formatNumber(stats.union)} />
          <StatTile label="সিটি কর্পোরেশন" value={formatNumber(stats.city_corporation)} />
          <StatTile label="যাচাইকৃত স্থান" value={formatNumber(stats.verified_places)} />
        </div>
        <p className="mt-3 flex items-start gap-2 text-xs text-muted">
          <ShieldCheck className="h-4 w-4 shrink-0 text-secondary" />
          সংখ্যাগুলো সরাসরি ডেটাবেস থেকে আসে। তথ্যসূত্র: বাংলাদেশ পরিসংখ্যান ব্যুরো (BBS), জাতীয় তথ্য বাতায়ন ও উন্মুক্ত উৎস।
        </p>
      </Section>
    </>
  );
}
