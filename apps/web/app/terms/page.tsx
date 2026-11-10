import Link from 'next/link';
import type { Metadata } from 'next';
import { Card, Section } from '@/components/ui';

export const dynamic = 'force-static';
export const metadata: Metadata = {
  title: 'ব্যবহারের শর্তাবলি',
  description: 'Elaka360 ব্যবহারের শর্ত: তথ্যের ধরন, ব্যবহারকারীর কনটেন্ট, মডারেশন ও সরকারের সঙ্গে সম্পর্ক।',
};

export default function TermsPage() {
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">ব্যবহারের শর্তাবলি</h1>
      <p className="font-en text-sm text-muted">Terms of use</p>
      <p className="mt-3 text-[15px]">Elaka360 ব্যবহার করে আপনি নিচের শর্তগুলো মেনে নিচ্ছেন। শর্তগুলো সহজ ভাষায় লেখা হয়েছে।</p>

      <Section title="১. তথ্য যেমন আছে তেমন">
        <Card className="space-y-2 p-4 text-[15px]">
          <p>
            সাইটের তথ্য উল্লেখিত উৎস থেকে নেওয়া এবং &ldquo;যেমন আছে তেমন&rdquo; দেওয়া হয়। আমরা তথ্য সঠিক রাখার চেষ্টা করি, কিন্তু কোনো তথ্য সম্পূর্ণ, নির্ভুল বা
            হালনাগাদ থাকবে — এমন নিশ্চয়তা দিতে পারি না। প্রতিটি তথ্যের উৎস ও প্রমাণের স্তর{' '}
            <Link href="/data-policy" className="font-medium text-secondary underline">
              তথ্য ও যাচাই নীতিতে
            </Link>{' '}
            ব্যাখ্যা করা আছে।
          </p>
          <p>
            <strong>গুরুত্বপূর্ণ সিদ্ধান্তের আগে</strong> — যেমন চিকিৎসা, আইনি বিষয়, সরকারি সেবা, ভ্রমণ বা অর্থ-সংক্রান্ত সিদ্ধান্ত — সংশ্লিষ্ট সরকারি দপ্তর বা
            প্রতিষ্ঠানের অফিসিয়াল উৎস থেকে তথ্য মিলিয়ে নিন।
          </p>
          <p>জরুরি অবস্থায় সাইটের তথ্যের জন্য অপেক্ষা না করে সরাসরি ৯৯৯ নম্বরে কল করুন।</p>
        </Card>
      </Section>

      <Section title="২. সরকারের সঙ্গে সম্পর্ক নেই">
        <Card className="p-4 text-[15px]">
          <p>
            Elaka360 একটি স্বতন্ত্র উদ্যোগ। এটি বাংলাদেশ সরকারের কোনো মন্ত্রণালয়, দপ্তর বা সংস্থার অংশ নয়, তাদের পক্ষে কাজ করে না, এবং তাদের অনুমোদনপ্রাপ্তও নয়।
            সাইটে সরকারি প্রতিষ্ঠানের নাম বা নম্বর থাকা মানে শুধু তথ্য দেওয়া, কোনো অংশীদারত্ব নয়।
          </p>
        </Card>
      </Section>

      <Section title="৩. আপনার দেওয়া কনটেন্ট">
        <Card className="space-y-2 p-4 text-[15px]">
          <p>রিভিউ, ছবি, নতুন স্থান বা সংশোধন জমা দিলে আপনি নিশ্চিত করছেন যে:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>তথ্যটি আপনার জানামতে সত্য, এবং প্রযোজ্য ক্ষেত্রে আপনি উৎস উল্লেখ করেছেন;</li>
            <li>ছবি বা লেখার স্বত্ব আপনার, অথবা তা ব্যবহারের অনুমতি আপনার আছে;</li>
            <li>এতে কোনো ব্যক্তির ব্যক্তিগত তথ্য, হয়রানি, ঘৃণাসূচক বক্তব্য, বিজ্ঞাপন বা বেআইনি কিছু নেই।</li>
          </ul>
          <p>
            জমা দেওয়া কনটেন্ট সাইটে দেখানো, সম্পাদনা ও সংরক্ষণের অনুমতি আপনি Elaka360-কে দিচ্ছেন। বিস্তারিত নিয়ম{' '}
            <Link href="/guidelines" className="font-medium text-secondary underline">
              অবদানের নির্দেশিকায়
            </Link>
            ।
          </p>
        </Card>
      </Section>

      <Section title="৪. মডারেশন">
        <Card className="p-4 text-[15px]">
          <p>
            নতুন স্থান ও সংশোধন পর্যালোচনার পরেই প্রকাশ হয়। রিভিউ সঙ্গে সঙ্গে প্রকাশ হয়, তবে যে কেউ অনুপযুক্ত রিভিউ রিপোর্ট করতে পারেন। নির্দেশিকা না মানলে
            আমরা কনটেন্ট সম্পাদনা, লুকানো বা মুছে ফেলতে পারি, এবং বারবার নিয়ম ভাঙলে অ্যাকাউন্ট সীমিত বা বন্ধ করতে পারি।
          </p>
        </Card>
      </Section>

      <Section title="৫. যা করা যাবে না">
        <Card className="p-4 text-[15px]">
          <ul className="list-disc space-y-1 pl-5">
            <li>সাইট বা এপিআই-এর ওপর অস্বাভাবিক চাপ তৈরি করা, বা নিরাপত্তা ব্যবস্থা এড়ানোর চেষ্টা করা;</li>
            <li>অন্য কারও পরিচয়ে অ্যাকাউন্ট খোলা বা ব্যবহার করা;</li>
            <li>ভুল তথ্য জেনেশুনে জমা দেওয়া।</li>
          </ul>
        </Card>
      </Section>

      <Section title="৬. পরিবর্তন">
        <Card className="space-y-2 p-4 text-[15px]">
          <p>সাইট ও এই শর্তাবলি সময়ের সঙ্গে বদলাতে পারে। বদলালে এই পাতা হালনাগাদ করা হবে।</p>
          <p>
            ব্যক্তিগত তথ্য কীভাবে ব্যবহার হয় তা জানতে{' '}
            <Link href="/privacy" className="font-medium text-secondary underline">
              গোপনীয়তা নীতি
            </Link>{' '}
            দেখুন। প্রশ্ন থাকলে{' '}
            <Link href="/contact" className="font-medium text-secondary underline">
              যোগাযোগ করুন
            </Link>
            ।
          </p>
        </Card>
      </Section>
    </div>
  );
}
