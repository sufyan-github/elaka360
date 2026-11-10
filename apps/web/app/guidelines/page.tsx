import Link from 'next/link';
import type { Metadata } from 'next';
import { Check, X } from 'lucide-react';
import { Card, Section } from '@/components/ui';

export const dynamic = 'force-static';
export const metadata: Metadata = {
  title: 'অবদানের নির্দেশিকা',
  description: 'Elaka360-এ তথ্য, ছবি ও রিভিউ দেওয়ার নিয়ম — কী গ্রহণ করা হয়, কী বাতিল হয়।',
};

const RULES: { title: string; body: string }[] = [
  {
    title: 'উৎস উল্লেখ করুন',
    body: 'নতুন তথ্য বা সংশোধনের সঙ্গে একটি যাচাইযোগ্য উৎস দিন — যেমন সরকারি ওয়েবসাইট, গেজেট, প্রতিষ্ঠানের নিজস্ব ওয়েবসাইট বা নির্ভরযোগ্য সংবাদপত্রের লিংক। সার্চ ইঞ্জিনের ফলাফলের পাতা উৎস হিসেবে গ্রহণ করা হয় না।',
  },
  {
    title: 'ব্যক্তিগত তথ্য নয়',
    body: 'সাধারণ ব্যক্তিদের ব্যক্তিগত ফোন নম্বর, বাড়ির ঠিকানা, পরিচয়পত্রের তথ্য বা ছবি দেবেন না। প্রতিষ্ঠানের প্রকাশ্য যোগাযোগের তথ্য দেওয়া যাবে।',
  },
  {
    title: 'বিজ্ঞাপন বা স্প্যাম নয়',
    body: 'প্রচারণামূলক লেখা, অপ্রাসঙ্গিক লিংক, একই তথ্য বারবার জমা দেওয়া বা নিজের ব্যবসার ভুয়া রিভিউ গ্রহণ করা হয় না।',
  },
  {
    title: 'নিজের তোলা ছবি',
    body: 'শুধু এমন ছবি দিন যা আপনি নিজে তুলেছেন বা ব্যবহারের অনুমতি আপনার আছে। ছবিতে মানুষের মুখ স্পষ্ট দেখা গেলে তাদের সম্মতি থাকা জরুরি।',
  },
  {
    title: 'রিভিউতে শ্রদ্ধাশীল থাকুন',
    body: 'নিজের অভিজ্ঞতা সৎভাবে লিখুন। গালাগাল, হুমকি, ঘৃণাসূচক বা বৈষম্যমূলক কথা এবং কোনো নির্দিষ্ট কর্মীকে নাম ধরে আক্রমণ করা যাবে না।',
  },
];

const REJECTED = [
  'উৎস ছাড়া বা যাচাই করা যায় না এমন তথ্য',
  'অনুমান বা শোনা কথার ভিত্তিতে দেওয়া সংখ্যা বা পরিসংখ্যান',
  'কারও ব্যক্তিগত তথ্য বা অনুমতি ছাড়া তোলা ছবি',
  'বিজ্ঞাপন, স্প্যাম বা অপ্রাসঙ্গিক লিংক',
  'অন্যের কাছ থেকে কপি করা লেখা বা ছবি',
  'অপমানজনক, হুমকিমূলক বা ঘৃণাসূচক ভাষা',
  'নিজেকে সরকারি প্রতিনিধি বা কোনো প্রতিষ্ঠানের কর্মকর্তা হিসেবে মিথ্যা পরিচয় দেওয়া',
];

export default function GuidelinesPage() {
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">অবদানের নির্দেশিকা</h1>
      <p className="font-en text-sm text-muted">Community contribution guidelines</p>
      <p className="mt-3 text-[15px]">
        আপনার দেওয়া তথ্য, ছবি ও রিভিউ অন্যদের কাজে লাগে। সবার জন্য তথ্য নির্ভরযোগ্য রাখতে নিচের নিয়মগুলো মেনে চলুন।
      </p>

      <Section title="মূল নিয়ম">
        <Card className="divide-y divide-line">
          {RULES.map((r) => (
            <div key={r.title} className="flex gap-3 px-4 py-3">
              <Check className="mt-1 h-5 w-5 shrink-0 text-verified" aria-hidden />
              <div>
                <h3 className="font-semibold">{r.title}</h3>
                <p className="mt-0.5 text-sm">{r.body}</p>
              </div>
            </div>
          ))}
        </Card>
      </Section>

      <Section title="যা বাতিল করা হয়">
        <Card className="p-4">
          <ul className="space-y-1.5 text-[15px]">
            {REJECTED.map((r) => (
              <li key={r} className="flex gap-2">
                <X className="mt-1 h-4 w-4 shrink-0 text-danger" aria-hidden />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </Card>
      </Section>

      <Section title="জমা দেওয়ার পর কী হয়">
        <Card className="space-y-2 p-4 text-[15px]">
          <p>
            নতুন স্থান ও সংশোধনের প্রস্তাব একজন পর্যালোচক দেখেন। প্রস্তাবটি অনুমোদিত, সংশোধনের জন্য ফেরত, অথবা বাতিল হতে পারে; আপনার প্রোফাইলে প্রতিটি প্রস্তাবের
            অবস্থা দেখা যাবে। শুধু উৎস যাচাইয়ের পরেই তথ্য সাইটে প্রকাশ হয় — কীভাবে, তা{' '}
            <Link href="/data-policy" className="font-medium text-secondary underline">
              তথ্য ও যাচাই নীতিতে
            </Link>{' '}
            লেখা আছে।
          </p>
          <p>রিভিউ জমা দেওয়ার পরই প্রকাশ হয়। কোনো রিভিউ নিয়ম ভাঙলে যে কেউ সেটি রিপোর্ট করতে পারেন, এবং পর্যালোচনার পর তা সরানো হতে পারে।</p>
          <p>বারবার নিয়ম ভাঙলে অ্যাকাউন্ট সীমিত বা বন্ধ করা হতে পারে।</p>
        </Card>
      </Section>

      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        <Link href="/contribute" className="inline-flex items-center justify-center rounded-chip bg-primary px-4 py-3 font-semibold text-on-primary hover:bg-primary-hover">
          তথ্য যোগ করুন
        </Link>
        <Link href="/terms" className="inline-flex items-center justify-center rounded-chip border border-line bg-surface px-4 py-3 font-semibold text-ink">
          ব্যবহারের শর্তাবলি
        </Link>
      </div>
    </div>
  );
}
