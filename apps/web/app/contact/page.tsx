import Link from 'next/link';
import type { Metadata } from 'next';
import { Phone } from 'lucide-react';
import { EVIDENCE_LABEL, toBnDigits } from '@elaka360/shared';
import { Card, Section } from '@/components/ui';
import { ContactForm } from './ContactForm';

export const dynamic = 'force-static';
export const metadata: Metadata = {
  title: 'যোগাযোগ',
  description: 'Elaka360 দলের কাছে প্রশ্ন, মতামত বা তথ্যের ভুল জানান।',
};

const FAQ: { q: string; a: React.ReactNode }[] = [
  {
    q: 'Elaka360-এর তথ্য কতটা নির্ভুল?',
    a: (
      <>
        প্রতিটি প্রকাশিত তথ্যের সঙ্গে তার উৎস ও প্রমাণের স্তর লেখা থাকে। এখন পর্যন্ত প্রকাশিত তথ্য &ldquo;{EVIDENCE_LABEL.secondary.bn}&rdquo; — অর্থাৎ
        উইকিপিডিয়া, জনশুমারির সংকলন বা সংবাদপত্রের মতো উৎস থেকে নেওয়া, সরকারিভাবে যাচাই করা নয়। তাই গুরুত্বপূর্ণ সিদ্ধান্তের আগে সংশ্লিষ্ট সরকারি
        দপ্তর বা প্রতিষ্ঠানের কাছ থেকে মিলিয়ে নিন। বিস্তারিত দেখুন{' '}
        <Link href="/data-policy" className="font-medium text-secondary underline">
          তথ্য ও যাচাই নীতি
        </Link>
        -তে।
      </>
    ),
  },
  {
    q: 'কোনো তথ্যে ভুল দেখলে কীভাবে জানাব?',
    a: (
      <>
        এই ফর্মে কোন পাতায় কী ভুল তা লিখুন, এবং সম্ভব হলে সঠিক তথ্যের একটি উৎসের লিংক দিন (যেমন সরকারি ওয়েবসাইট বা গেজেট)। উৎস ছাড়া কোনো সংশোধন
        প্রকাশ করা হয় না; পর্যালোচনার পরেই পরিবর্তন সাইটে আসে।
      </>
    ),
  },
  {
    q: 'নতুন কোনো স্থান বা প্রতিষ্ঠান কীভাবে যোগ করব?',
    a: (
      <>
        সাইন-ইন করে{' '}
        <Link href="/contribute" className="font-medium text-secondary underline">
          তথ্য যোগ করুন
        </Link>{' '}
        পাতা থেকে প্রস্তাব পাঠাতে পারেন। প্রস্তাবটি পর্যালোচনা করা হয় এবং উৎস যাচাইয়ের পরেই প্রকাশ হয়। নিয়মগুলো পড়ুন{' '}
        <Link href="/guidelines" className="font-medium text-secondary underline">
          অবদানের নির্দেশিকায়
        </Link>
        ।
      </>
    ),
  },
  {
    q: 'আমার পাঠানো তথ্য কীভাবে ব্যবহার হয়?',
    a: (
      <>
        এই ফর্মে দেওয়া বিষয়, বার্তা ও (ঐচ্ছিক) ইমেইল শুধু আপনার বার্তার বিষয়ে কাজ করা ও উত্তর দেওয়ার জন্য সংরক্ষণ করা হয়। বিস্তারিত{' '}
        <Link href="/privacy" className="font-medium text-secondary underline">
          গোপনীয়তা নীতিতে
        </Link>
        ।
      </>
    ),
  },
];

export default function ContactPage() {
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">যোগাযোগ</h1>
      <p className="font-en text-sm text-muted">Contact the Elaka360 team</p>

      <a href="tel:999" className="mt-4 flex items-center gap-3 rounded-card border border-danger bg-danger-tint px-4 py-3 text-ink">
        <Phone className="h-5 w-5 shrink-0 text-danger" aria-hidden />
        <span className="text-sm">
          <strong>জরুরি প্রয়োজনে এই ফর্ম ব্যবহার করবেন না।</strong> পুলিশ, ফায়ার সার্ভিস বা অ্যাম্বুলেন্সের জন্য{' '}
          <span className="font-bold text-danger">{toBnDigits('999')}</span> নম্বরে কল করুন।
        </span>
      </a>

      <Section title="বার্তা পাঠান">
        <Card className="p-4">
          <p className="mb-4 text-sm text-muted">প্রশ্ন, মতামত, তথ্যের ভুল বা সহযোগিতার প্রস্তাব — এই ফর্মে লিখে পাঠান।</p>
          <ContactForm />
        </Card>
      </Section>

      <Section title="সাধারণ প্রশ্ন">
        <Card className="divide-y divide-line">
          {FAQ.map((f) => (
            <details key={f.q} className="group px-4 py-3">
              <summary className="flex cursor-pointer list-none items-start justify-between gap-3 font-semibold [&::-webkit-details-marker]:hidden">
                <h3 className="text-[15px]">{f.q}</h3>
                <span className="text-lg leading-none text-muted transition-transform group-open:rotate-45 motion-reduce:transition-none" aria-hidden>
                  +
                </span>
              </summary>
              <p className="mt-2 text-sm">{f.a}</p>
            </details>
          ))}
        </Card>
      </Section>
    </div>
  );
}
