import Link from 'next/link';
import type { Metadata } from 'next';
import { FilePlus2, MessageSquareWarning, PencilLine, ShieldCheck } from 'lucide-react';
import { Card, Section } from '@/components/ui';

export const metadata: Metadata = { title: 'তথ্য যোগ করুন' };

const ACTIONS = [
  { type: 'new_place', title: 'নতুন স্থান যোগ করুন', body: 'স্কুল, হাসপাতাল, অফিস, দর্শনীয় স্থান বা ব্যবসা।', Icon: FilePlus2 },
  { type: 'correction', title: 'ভুল তথ্য সংশোধন', body: 'কোনো পাতার নাম, ঠিকানা, ফোন বা অন্য তথ্য ভুল হলে।', Icon: PencilLine },
  { type: 'report', title: 'সমস্যা জানান', body: 'বন্ধ হয়ে যাওয়া স্থান, ডুপ্লিকেট বা আপত্তিকর তথ্য।', Icon: MessageSquareWarning },
];

export default function ContributePage() {
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">আপনার এলাকার তথ্য যোগ করুন</h1>
      <p className="mt-1 text-sm text-muted">প্রতিটি অবদান মডারেটর যাচাই করেন। অনুমোদনের পর তথ্যটি “কমিউনিটির তথ্য” লেখাসহ দেখানো হয়; উৎস যাচাই হলে “উৎসসহ” হয়।</p>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {ACTIONS.map(({ type, title, body, Icon }) => (
          <Link key={type} href={`/contribute/new?type=${type}`} className="rounded-card border border-line bg-surface p-4 shadow-card hover:border-secondary">
            <Icon className="h-7 w-7 text-secondary" aria-hidden />
            <span className="mt-2 block font-semibold">{title}</span>
            <span className="block text-sm text-muted">{body}</span>
          </Link>
        ))}
      </div>
      <Section title="কীভাবে কাজ করে">
        <Card className="p-4 text-sm">
          <ol className="list-decimal space-y-1 pl-5">
            <li>ধরন বেছে নিন ও তথ্য লিখুন (বাংলা নাম আবশ্যক)।</li>
            <li>অবস্থান দিন — “আমার অবস্থান” বা পরে মডারেটর ঠিক করবেন।</li>
            <li>উৎসের লিংক দিন (সরকারি পোর্টাল, প্রতিষ্ঠানের ওয়েবসাইট ইত্যাদি) — এতে যাচাই দ্রুত হয়।</li>
            <li>নিশ্চিত করে জমা দিন। অবস্থা দেখুন প্রোফাইলে: জমা → পর্যালোচনা → অনুমোদিত / সংশোধন প্রয়োজন / বাতিল।</li>
          </ol>
          <p className="mt-3 flex items-start gap-2 text-muted"><ShieldCheck className="h-4 w-4 shrink-0 text-secondary" aria-hidden />
            কারও ব্যক্তিগত তথ্য (বাড়ির ঠিকানা, ব্যক্তিগত ফোন নম্বর) দেবেন না। <Link href="/guidelines" className="underline">নির্দেশিকা</Link></p>
        </Card>
      </Section>
    </div>
  );
}
