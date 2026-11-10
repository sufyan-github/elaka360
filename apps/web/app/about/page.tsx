import Link from 'next/link';
import type { Metadata } from 'next';
import { EVIDENCE_LABEL } from '@elaka360/shared';
import { Card, Section } from '@/components/ui';

export const dynamic = 'force-static';
export const metadata: Metadata = {
  title: 'আমাদের সম্পর্কে',
  description: 'Elaka360 কী, তথ্য কোথা থেকে আসে, কোন তথ্য প্রকাশ করা হয় এবং সামনের পরিকল্পনা।',
};

export default function AboutPage() {
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">আমাদের সম্পর্কে</h1>
      <p className="font-en text-sm text-muted">About Elaka360</p>

      <Section title="আমাদের লক্ষ্য">
        <Card className="space-y-2 p-4 text-[15px]">
          <p>
            Elaka360-এর লক্ষ্য খুব সহজ: বাংলাদেশের মানুষ যেন নিজের এলাকার নির্ভরযোগ্য তথ্য — প্রশাসনিক এলাকা, প্রতিষ্ঠান, সেবা ও জরুরি নম্বর — এক
            জায়গায়, বাংলায় এবং উৎসসহ খুঁজে পান।
          </p>
          <p>
            আমরা মনে করি তথ্যের পাশে তার উৎস দেখানো জরুরি। তাই প্রতিটি প্রকাশিত তথ্যের সঙ্গে কোথা থেকে নেওয়া হয়েছে তা লেখা থাকে, আর যে তথ্য এখনো
            মিলিয়ে দেখা হয়নি তা আমরা প্রকাশ করি না।
          </p>
          <p className="text-sm text-muted">
            Elaka360 একটি স্বতন্ত্র উদ্যোগ। এটি বাংলাদেশ সরকার বা কোনো সরকারি সংস্থার অংশ নয়, এবং কোনো সরকারি সংস্থা এটি অনুমোদন করেনি।
          </p>
        </Card>
      </Section>

      <Section title="তথ্য কীভাবে কাজ করে">
        <Card className="space-y-3 p-4 text-[15px]">
          <p>প্রতিটি তথ্যের একটি প্রমাণের স্তর থাকে। সাইটে এগুলো এভাবে লেখা থাকে:</p>
          <ul className="space-y-1.5">
            {(['official', 'secondary', 'community', 'unverified'] as const).map((k) => (
              <li key={k} className="flex flex-wrap items-baseline gap-x-2">
                <span className="rounded-full bg-tint px-2 py-0.5 text-xs font-medium text-primary">{EVIDENCE_LABEL[k].bn}</span>
                <span className="text-sm text-muted">{EVIDENCE_LABEL[k].hint_bn}</span>
              </li>
            ))}
          </ul>
          <p>
            শুধু <strong>{EVIDENCE_LABEL.official.bn}</strong> বা <strong>{EVIDENCE_LABEL.secondary.bn}</strong> তথ্য, যার উৎসের নাম জানা আছে,
            সাইটে প্রকাশ করা হয়। কমিউনিটির তথ্য ও যাচাই-বাকি তথ্য পর্যালোচনার জন্য রাখা থাকে, প্রকাশ করা হয় না।
          </p>
          <p>
            এখন পর্যন্ত প্রকাশিত সব তথ্যই দ্বিতীয় উৎস থেকে নেওয়া — যেমন উইকিপিডিয়া, বিবিএস জনশুমারি ২০২২-এর citypopulation.de সংকলন এবং সংবাদপত্র।
            কোনো তথ্য এখনো সরকারিভাবে যাচাই করা হয়নি।
          </p>
          <p>
            জেলার নিচের প্রশাসনিক স্তর (উপজেলা, ইউনিয়ন) একটি কমিউনিটি ডেটাসেট থেকে এসেছে। সরকারি তালিকার সঙ্গে মিলিয়ে না দেখা পর্যন্ত এগুলোর
            বেশিরভাগ দেখানো হচ্ছে না।
          </p>
          <p>
            Elaka360 এখন <strong>রাজশাহী পাইলট</strong> পর্যায়ে আছে: প্রতিষ্ঠান ও স্থানের তথ্য আপাতত রাজশাহী জেলার অল্প কয়েকটি জায়গার মধ্যে সীমিত।
          </p>
        </Card>
      </Section>

      <Section title="সামনের পরিকল্পনা">
        <Card className="p-4 text-[15px]">
          <p className="mb-2 text-sm text-muted">নিচের কাজগুলো আমাদের পরিকল্পনায় আছে। এগুলো প্রতিশ্রুতি নয়, সময়সূচিও নির্ধারিত নয়।</p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>উপজেলা ও ইউনিয়নের তালিকা সরকারি উৎসের সঙ্গে মিলিয়ে ধাপে ধাপে প্রকাশ করা।</li>
            <li>রাজশাহীর বাইরে অন্য জেলায় প্রতিষ্ঠান ও সেবার তথ্য যোগ করা।</li>
            <li>ব্যবহারকারীদের সংশোধন ও নতুন স্থানের প্রস্তাব পর্যালোচনা করে প্রকাশ করা।</li>
            <li>ইংরেজি সংস্করণ চালু করা।</li>
          </ul>
        </Card>
      </Section>

      <Section title="আরও জানুন">
        <Card className="divide-y divide-line">
          {[
            { href: '/data-policy', label: 'তথ্য ও যাচাই নীতি', sub: 'প্রমাণের স্তর, উৎসের তালিকা ও জানা ঘাটতি' },
            { href: '/guidelines', label: 'অবদানের নির্দেশিকা', sub: 'তথ্য যোগ বা সংশোধনের নিয়ম' },
            { href: '/contribute', label: 'তথ্য যোগ করুন', sub: 'নতুন স্থান বা সংশোধন প্রস্তাব করুন' },
            { href: '/contact', label: 'যোগাযোগ', sub: 'প্রশ্ন বা মতামত পাঠান' },
          ].map((l) => (
            <Link key={l.href} href={l.href} className="block px-4 py-3 hover:bg-tint">
              <span className="block font-semibold text-primary">{l.label}</span>
              <span className="block text-sm text-muted">{l.sub}</span>
            </Link>
          ))}
        </Card>
      </Section>
    </div>
  );
}
