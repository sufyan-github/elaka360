'use client';

import { useState } from 'react';
import type { DataSource } from '@elaka360/shared';
import type { ActionState } from '@/app/(admin)/actions';
import { HIGH_TRUST_TYPES, SOURCE_TYPES, isSearchUrl } from '@/lib/labels';
import { ActionForm, Field, SubmitButton } from './ActionForm';

/** Create (no `source`) or edit a data source, with the API's rules checked as you type. */
export function SourceForm({ action, source }: { action: (prev: ActionState, fd: FormData) => Promise<ActionState>; source?: DataSource }) {
  const s = source;
  const p = s ? `sf-${s.id}` : 'sf-new';
  const [url, setUrl] = useState(s?.url ?? '');
  const [type, setType] = useState(s?.source_type ?? 'unknown');
  const [trust, setTrust] = useState(String(s?.trust_level ?? 2));
  const [active, setActive] = useState(s?.active ?? true);
  const searchUrl = url.trim() !== '' && isSearchUrl(url.trim());
  const highTrustBad = Number(trust) >= 4 && !HIGH_TRUST_TYPES.includes(type);
  const invalid = searchUrl || highTrustBad;
  const deactivating = s && s.active && !active;

  return (
    <ActionForm action={action} resetOnSuccess={!s} className="space-y-3"
      confirm={deactivating ? `উৎসটি নিষ্ক্রিয় করবেন? এটি ${s.usage_count ?? 0}টি রেকর্ডে ব্যবহৃত; নতুন যাচাইয়ে আর বেছে নেওয়া যাবে না।` : undefined}>
      <div className="grid gap-3 md:grid-cols-2">
        {!s && (
          <Field label="কী" en="key (A–Z, 0–9, _)" htmlFor={`${p}-key`} required>
            <input id={`${p}-key`} name="key" className="input font-en uppercase" required minLength={2} maxLength={40} pattern="[A-Za-z0-9_]+" />
          </Field>
        )}
        <Field label="নাম" en="name" htmlFor={`${p}-name`} required className={s ? 'md:col-span-2' : ''}>
          <input id={`${p}-name`} name="name" className="input" required minLength={3} maxLength={200} defaultValue={s?.name ?? ''} />
        </Field>
        <Field label="URL" en="url" htmlFor={`${p}-url`} className="md:col-span-2"
          hint={searchUrl ? <span className="text-danger">সার্চ ফলাফলের পাতা উৎস নয়; মূল নথির লিংক দিন।</span> : 'প্রকাশিত রেকর্ডের উৎসে URL থাকা বাধ্যতামূলক।'}>
          <input id={`${p}-url`} name="url" type="url" className="input font-en" value={url} onChange={(e) => setUrl(e.target.value)} maxLength={500}
            aria-invalid={searchUrl} aria-describedby={`${p}-url-hint`} />
        </Field>
        <Field label="ধরন" en="source_type" htmlFor={`${p}-type`}>
          <select id={`${p}-type`} name="source_type" className="input font-en" value={type} onChange={(e) => setType(e.target.value)}>
            {SOURCE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="আস্থার স্তর" en="trust_level 1–5" htmlFor={`${p}-trust`}
          hint={highTrustBad ? <span className="text-danger">৪–৫ শুধু government_portal, gazette, census-এর জন্য।</span> : '৪–৫: সরকারি পোর্টাল/গেজেট/আদমশুমারি; সরকারি স্তরের যাচাইয়ে লাগে।'}>
          <select id={`${p}-trust`} name="trust_level" className="input" value={trust} onChange={(e) => setTrust(e.target.value)} aria-invalid={highTrustBad} aria-describedby={`${p}-trust-hint`}>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n} disabled={n >= 4 && !HIGH_TRUST_TYPES.includes(type)}>{n}</option>)}
          </select>
        </Field>
        <Field label="লাইসেন্স" en="license" htmlFor={`${p}-license`}>
          <input id={`${p}-license`} name="license" className="input font-en" maxLength={120} defaultValue={s?.license ?? ''} />
        </Field>
        <Field label="প্রতিষ্ঠান" en="organization" htmlFor={`${p}-org`}>
          <input id={`${p}-org`} name="organization" className="input" maxLength={120} defaultValue={s?.organization ?? ''} />
        </Field>
        <Field label="দেখার তারিখ" en="access_date" htmlFor={`${p}-access`}>
          <input id={`${p}-access`} name="access_date" type="date" className="input font-en" defaultValue={s?.access_date ?? ''} />
        </Field>
        <Field label="প্রকাশের তারিখ" en="publication_date" htmlFor={`${p}-pub`}>
          <input id={`${p}-pub`} name="publication_date" type="date" className="input font-en" defaultValue={s?.publication_date ?? ''} />
        </Field>
        <Field label="প্রমাণ-নোট" en="evidence_notes" htmlFor={`${p}-notes`} className="md:col-span-2">
          <textarea id={`${p}-notes`} name="evidence_notes" className="input min-h-16" maxLength={1000} defaultValue={s?.evidence_notes ?? ''} />
        </Field>
        {s && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name="active" className="h-4 w-4" checked={active} onChange={(e) => setActive(e.target.checked)} /> সক্রিয় <span className="font-en text-xs text-muted">active</span>
          </label>
        )}
      </div>
      <SubmitButton disabled={invalid}>{s ? 'সংরক্ষণ' : 'উৎস যোগ করুন'}</SubmitButton>
    </ActionForm>
  );
}
