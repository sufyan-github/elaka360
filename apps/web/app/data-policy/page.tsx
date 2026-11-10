import fs from 'node:fs';
import path from 'node:path';
import Link from 'next/link';
import type { Metadata } from 'next';
import { ExternalLink } from 'lucide-react';
import { EVIDENCE_LABEL, type EvidenceLevel } from '@elaka360/shared';
import { Card, Section } from '@/components/ui';

// Rendered once at build time from the committed seed (data/seed/**), so names and URLs match it exactly.
export const dynamic = 'force-static';
export const metadata: Metadata = {
  title: 'তথ্য ও যাচাই নীতি',
  description: 'Elaka360-এ তথ্যের প্রমাণের স্তর, কোন তথ্য প্রকাশিত হয়, উৎসের তালিকা, সংশোধনের নিয়ম ও জানা ঘাটতি।',
};

/* ---------------------------------------------------------------- build-time seed reading */

function seedDir(): string {
  let dir = process.cwd();
  for (let i = 0; i < 5; i++) {
    const candidate = path.join(dir, 'data', 'seed');
    if (fs.existsSync(path.join(candidate, 'reference', 'data_sources.csv'))) return candidate;
    dir = path.dirname(dir);
  }
  throw new Error('data-policy: data/seed not found (looked upwards from the web app directory)');
}

/** Minimal RFC 4180 parser (quoted fields, doubled quotes, CRLF), returning objects keyed by the header row. */
function readCsv(file: string): Record<string, string>[] {
  const text = fs.readFileSync(path.join(seedDir(), file), 'utf8').replace(/^\uFEFF/, '');
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else field += c;
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [header, ...body] = rows.filter((r) => r.some((x) => x !== ''));
  return body.map((r) => Object.fromEntries(header!.map((h, i) => [h, r[i] ?? ''])));
}

type Source = { key: string; name: string; url: string };

function loadSources() {
  const all = readCsv('reference/data_sources.csv').map((r) => ({ key: r.key!, name: r.name!, url: r.url ?? '' }));
  const published = new Set<string>();
  const heldBack = new Set<string>();
  for (const a of readCsv('geo/admin_areas.csv')) {
    if (a.production_eligible === 'True') {
      if (a.evidence_source) published.add(a.evidence_source);
      if (a.population_source) published.add(a.population_source);
    } else if (a.evidence_level === 'community') heldBack.add(a.data_source || a.evidence_source || '');
  }
  for (const p of readCsv('pilot_rajshahi/places.csv')) if (p.production_eligible === 'True' && p.source) published.add(p.source);
  for (const h of readCsv('reference/emergency_hotlines.csv')) if ((h.evidence_level === 'official' || h.evidence_level === 'secondary') && h.source) published.add(h.source);

  const byKey = new Map(all.map((s) => [s.key, s]));
  const pick = (keys: Set<string>) => all.filter((s) => keys.has(s.key) && s.url) as Source[];
  const missing = [...published].filter((k) => !byKey.has(k));
  if (missing.length) throw new Error(`data-policy: published records cite unknown source keys: ${missing.join(', ')}`);
  return { published: pick(published), heldBack: pick(new Set([...heldBack].filter((k) => !published.has(k)))) };
}

const GAP_AREA_BN: Record<string, string> = {
  unions: 'ইউনিয়ন',
  upazilas: 'উপজেলা',
  codes: 'জিওকোড',
  pourashavas: 'পৌরসভা',
  'wards/villages': 'ওয়ার্ড ও গ্রাম',
  area: 'আয়তন',
  population: 'জনসংখ্যা',
  places: 'স্থান ও প্রতিষ্ঠান',
};

/* ---------------------------------------------------------------- page */

const LEVELS: EvidenceLevel[] = ['official', 'secondary', 'community', 'unverified'];

export default function DataPolicyPage() {
  const { published, heldBack } = loadSources();
  const gaps = readCsv('qa/known_gaps.csv');

  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">তথ্য ও যাচাই নীতি</h1>
      <p className="font-en text-sm text-muted">Data &amp; verification policy</p>
      <p className="mt-3 text-[15px]">
        Elaka360-এ কোন তথ্য দেখানো হবে আর কোনটি হবে না, তা নিচের নিয়মে ঠিক হয়। মূল কথা: <strong>প্রতিটি তথ্যের পাশে লেখা থাকে সেটি কোন উৎস থেকে এসেছে এবং যাচাই হয়েছে কি না।</strong>
      </p>

      <Section title="প্রমাণের চারটি স্তর">
        <Card className="divide-y divide-line">
          {LEVELS.map((k) => (
            <div key={k} className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-tint px-2.5 py-0.5 text-sm font-medium text-primary">{EVIDENCE_LABEL[k].bn}</span>
                <span className="font-en text-xs text-muted">{EVIDENCE_LABEL[k].en}</span>
                <span className={`ml-auto text-xs font-medium ${k === 'official' || k === 'secondary' ? 'text-verified' : 'text-muted'}`}>
                  {k === 'official' || k === 'secondary' ? 'উৎসসহ' : 'দেখানো হয়, “যাচাই করা হয়নি” লেখাসহ'}
                </span>
              </div>
              <p className="mt-1 text-sm">{EVIDENCE_LABEL[k].hint_bn}</p>
            </div>
          ))}
        </Card>
        <p className="mt-2 text-sm text-muted">
          &ldquo;যাচাইকৃত&rdquo; শব্দটি শুধু সরকারিভাবে যাচাই করা তথ্যের জন্য ব্যবহার করা হয়। এখন পর্যন্ত কোনো তথ্য এই স্তরে পৌঁছায়নি।
        </p>
      </Section>

      <Section title="উৎসসহ আর যাচাই-না-করা তথ্যের পার্থক্য">
        <Card className="space-y-2 p-4 text-[15px]">
          <p>একটি তথ্যকে &ldquo;উৎসসহ&rdquo; (প্রকাশযোগ্য) ধরা হয় কেবল তখনই, যখন:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              তার প্রমাণের স্তর &ldquo;{EVIDENCE_LABEL.official.bn}&rdquo; অথবা &ldquo;{EVIDENCE_LABEL.secondary.bn}&rdquo;, <strong>এবং</strong>
            </li>
            <li>যে উৎস থেকে নেওয়া হয়েছে তার নাম (এবং যেখানে সম্ভব লিংক) রেকর্ড করা আছে।</li>
          </ul>
          <p>বাকি তথ্যও দেখানো হয়, যাতে আপনি নিজের এলাকা খুঁজে পান এবং ভুল ধরিয়ে দিতে পারেন। তবে এমন প্রতিটি পাতার ওপরে &ldquo;যাচাই করা হয়নি&rdquo; সতর্কবার্তা থাকে এবং সার্চ ইঞ্জিনে সেগুলো ইনডেক্স করতে দেওয়া হয় না। জরুরি হটলাইন কখনোই উৎস ছাড়া দেখানো হয় না, আর ভবিষ্যতের উন্মুক্ত ডেটা (Open Data) রপ্তানিতেও শুধু উৎসসহ তথ্য থাকবে। এই নিয়মগুলো ডাটাবেসের স্তরেই প্রয়োগ করা হয়।</p>
        </Card>
      </Section>

      <Section title="বেশিরভাগ উপজেলা ও ইউনিয়ন কেন &ldquo;যাচাই করা হয়নি&rdquo;">
        <Card className="space-y-2 p-4 text-[15px]">
          <p>
            বিভাগ, জেলা ও সিটি কর্পোরেশনের তালিকা দ্বিতীয় উৎস থেকে মিলিয়ে প্রকাশ করা হয়েছে। কিন্তু জেলার নিচের স্তরের (উপজেলা, ইউনিয়ন) পূর্ণ তালিকা এসেছে
            একটি কমিউনিটি ডেটাসেট থেকে, যাতে কিছু নতুন উপজেলা ও ইউনিয়ন বাদ পড়েছে বা ভুল জায়গায় আছে। সরকারি তালিকার সঙ্গে মিলিয়ে না দেখা পর্যন্ত এগুলো
            &ldquo;যাচাই করা হয়নি&rdquo; হিসেবে দেখানো হয়।
          </p>
          <p>
            ব্যতিক্রম: রাজশাহী পাইলটের অংশ হিসেবে রাজশাহী জেলার উপজেলাগুলো, এবং আলাদা উৎস পাওয়া অল্প কয়েকটি এলাকা উৎসসহ আছে।
          </p>
        </Card>
      </Section>

      <Section title="জনসংখ্যার হিসাব সম্পর্কে">
        <Card className="p-4 text-[15px]">
          <p>
            জনসংখ্যার সংখ্যাগুলো বিবিএস জনশুমারি ২০২২ থেকে (citypopulation.de-এর সংকলনের মাধ্যমে) নেওয়া, তবে সব স্তরে একই ভিত্তি নয়: বিভাগ ও জেলার জন্য
            <strong> সমন্বিত (adjusted)</strong> সংখ্যা, আর রাজশাহী জেলার উপজেলাগুলোর জন্য <strong>গণনাকৃত (enumerated)</strong> সংখ্যা ব্যবহার করা হয়েছে।
            তাই উপজেলাগুলোর যোগফল জেলার মোটের সঙ্গে হুবহু না-ও মিলতে পারে।
          </p>
        </Card>
      </Section>

      <Section title="সংশোধন কীভাবে হয়">
        <Card className="p-4 text-[15px]">
          <ol className="list-decimal space-y-1.5 pl-5">
            <li>
              কোনো ভুল দেখলে{' '}
              <Link href="/contact" className="font-medium text-secondary underline">
                যোগাযোগ ফর্মে
              </Link>{' '}
              জানান, অথবা সাইন-ইন করে{' '}
              <Link href="/contribute" className="font-medium text-secondary underline">
                সংশোধন প্রস্তাব
              </Link>{' '}
              পাঠান — সঙ্গে সঠিক তথ্যের উৎস দিন।
            </li>
            <li>Elaka360 দলের একজন পর্যালোচক উৎসটি দেখে প্রস্তাবটি অনুমোদন, সংশোধনের অনুরোধ বা বাতিল করেন।</li>
            <li>অনুমোদিত হলে তথ্য হালনাগাদ হয় এবং নতুন উৎস তথ্যের সঙ্গে লেখা থাকে। পরিবর্তনের রেকর্ড রাখা হয়।</li>
          </ol>
          <p className="mt-2 text-sm text-muted">
            নিয়মগুলো বিস্তারিত দেখুন{' '}
            <Link href="/guidelines" className="text-secondary underline">
              অবদানের নির্দেশিকায়
            </Link>
            ।
          </p>
        </Card>
      </Section>

      <Section title="প্রকাশিত তথ্যের উৎস">
        <Card className="divide-y divide-line">
          {published.map((s) => (
            <a key={s.key} href={s.url} target="_blank" rel="noreferrer" className="flex items-start gap-2 px-4 py-2.5 hover:bg-tint">
              <span lang="en" className="min-w-0 flex-1 font-en text-sm break-words">
                {s.name}
              </span>
              <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
                  <span className="sr-only">(নতুন ট্যাবে খুলবে)</span>
            </a>
          ))}
        </Card>
        <p className="mt-2 text-xs text-muted">তালিকাটি সাইটের এই সংস্করণের ডেটাসেট থেকে তৈরি।</p>

        {heldBack.length > 0 && (
          <>
            <h3 className="mt-4 mb-2 font-semibold">যাচাইয়ের অপেক্ষায় থাকা তথ্যের উৎস</h3>
            <Card className="divide-y divide-line">
              {heldBack.map((s) => (
                <a key={s.key} href={s.url} target="_blank" rel="noreferrer" className="flex items-start gap-2 px-4 py-2.5 hover:bg-tint">
                  <span className="min-w-0 flex-1">
                    <span lang="en" className="block font-en text-sm break-words">
                      {s.name}
                    </span>
                    <span className="block text-xs text-muted">{EVIDENCE_LABEL.community.bn} — উপজেলা ও ইউনিয়নের তালিকা এখান থেকে এসেছে</span>
                  </span>
                  <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
                  <span className="sr-only">(নতুন ট্যাবে খুলবে)</span>
                </a>
              ))}
            </Card>
          </>
        )}
      </Section>

      <Section title="জানা ঘাটতি">
        <p className="mb-2 text-sm">ডেটাসেটে যেসব ঘাটতি আমাদের জানা আছে এবং সেগুলো পূরণের পরিকল্পনা (প্রকল্পের মান-যাচাই তালিকা থেকে, ইংরেজিতে):</p>
        <Card className="divide-y divide-line">
          {gaps.map((g, i) => (
            <div key={i} className="px-4 py-3">
              <span className="rounded-full border border-line px-2 py-0.5 text-xs">{GAP_AREA_BN[g.area!] ?? g.area}</span>
              <p lang="en" className="mt-1.5 font-en text-sm">
                {g.gap}
              </p>
              <p lang="en" className="mt-0.5 font-en text-xs text-muted">
                <span lang="bn" className="font-bn">
                  পরিকল্পিত সমাধান:
                </span>{' '}
                {g.fix}
              </p>
            </div>
          ))}
        </Card>
      </Section>
    </div>
  );
}
