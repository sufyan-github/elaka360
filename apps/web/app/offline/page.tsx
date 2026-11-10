import Link from 'next/link';
import type { Metadata } from 'next';
import { Phone, Siren, WifiOff } from 'lucide-react';
import { EVIDENCE_LABEL, toBnDigits, type EvidenceLevel } from '@elaka360/shared';
import { Card, Section } from '@/components/ui';
import hotlinesJson from '@/public/data/hotlines.json';

// Pre-rendered at build time (no API call) so the service worker can cache it as the offline fallback.
export const dynamic = 'force-static';
export const metadata: Metadata = { title: 'অফলাইন', robots: { index: false } };

type Hotline = { number: string; name_bn: string; name_en: string; evidence_level: EvidenceLevel };
const hotlines = hotlinesJson as Hotline[];

export default function OfflinePage() {
  return (
    <div className="pt-6">
      <h1 className="flex items-center gap-2 text-2xl font-bold">
        <WifiOff className="h-7 w-7 text-muted" aria-hidden /> ইন্টারনেট সংযোগ নেই
      </h1>
      <p className="mt-2 text-[15px]">
        এই পাতাটি এখন লোড করা যাচ্ছে না। সংযোগ ফিরে এলে আবার চেষ্টা করুন। আগে খোলা কিছু পাতা অফলাইনেও দেখা যেতে পারে, তবে সেগুলোর তথ্য পুরোনো হতে
        পারে।
      </p>
      <p className="mt-1 font-en text-sm text-muted">You are offline. Previously opened pages may still work, but may be out of date.</p>

      <Link href="/emergency" className="mt-4 flex items-center justify-between rounded-card bg-danger px-4 py-3 font-semibold text-on-danger shadow-card">
        <span className="flex items-center gap-2">
          <Siren className="h-5 w-5" aria-hidden /> জরুরি সেবার পাতা খুলুন
        </span>
        <span aria-hidden>→</span>
      </Link>

      <Section title="জরুরি ও সেবা হটলাইন">
        <p className="mb-3 text-sm">
          জীবন বা সম্পদের ঝুঁকিতে <strong>{toBnDigits('999')}</strong> নম্বরে কল করুন — এটি বাংলাদেশের জাতীয় জরুরি সেবা নম্বর (পুলিশ, ফায়ার সার্ভিস, অ্যাম্বুলেন্স)।
          ফোন কল করতে ইন্টারনেট লাগে না।
        </p>
        <Card className="divide-y divide-line">
          {hotlines.map((h) => (
            <a key={h.number} href={`tel:${h.number}`} className="flex items-center gap-3 px-4 py-3">
              <span className="w-16 shrink-0 text-xl font-bold text-danger">{toBnDigits(h.number)}</span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{h.name_bn}</span>
                <span className="block font-en text-xs text-muted">{h.name_en}</span>
                <span className="block text-[11px] text-muted">{EVIDENCE_LABEL[h.evidence_level]?.bn ?? EVIDENCE_LABEL.unverified.bn}</span>
              </span>
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary text-on-primary" aria-hidden>
                <Phone className="h-5 w-5" />
              </span>
              <span className="sr-only">— কল করুন</span>
            </a>
          ))}
        </Card>
        <p className="mt-2 text-xs text-muted">
          {hotlines.every((h) => h.evidence_level === 'secondary')
            ? `এই নম্বরগুলো ${EVIDENCE_LABEL.secondary.bn} — ${EVIDENCE_LABEL.secondary.hint_bn}`
            : 'প্রতিটি নম্বরের নিচে তার তথ্যের স্তর লেখা আছে।'}{' '}
          তালিকাটি অ্যাপের এই সংস্করণ তৈরির সময় সংরক্ষিত হয়েছে, তাই হালনাগাদ না-ও হতে পারে।
        </p>
      </Section>
    </div>
  );
}
