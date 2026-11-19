'use client';

import { useState } from 'react';
import type { DataSource, EvidenceLevel } from '@elaka360/shared';
import { EVIDENCE_LABEL, toBnDigits } from '@elaka360/shared';
import type { ActionState } from '@/app/(admin)/actions';
import { EVIDENCE_LEVELS, PUBLISHABLE } from '@/lib/labels';
import { ActionForm, Field, SubmitButton } from './ActionForm';

export interface VerifyCurrent {
  evidence_level: EvidenceLevel;
  evidence_source_id: number | null;
  production_eligible: boolean;
  verification_notes: string | null;
}

/**
 * Verification decision under the trust policy: publication only for official/secondary evidence
 * with a named source that has a URL; official needs a trust 4–5 source. The API enforces the same.
 */
export function VerifyForm({ action, current, sources, idPrefix = 'v' }: {
  action: (prev: ActionState, fd: FormData) => Promise<ActionState>; current: VerifyCurrent; sources: DataSource[]; idPrefix?: string;
}) {
  const [level, setLevel] = useState<EvidenceLevel>(current.evidence_level);
  const [srcId, setSrcId] = useState<string>(current.evidence_source_id ? String(current.evidence_source_id) : '');
  const [publish, setPublish] = useState(current.production_eligible);
  const active = sources.filter((s) => s.active || s.id === current.evidence_source_id);
  const src = active.find((s) => String(s.id) === srcId) ?? null;

  const needsSource = PUBLISHABLE.includes(level);
  const officialTooLow = level === 'official' && src !== null && src.trust_level < 4;
  const canPublish = needsSource && !!src && !!src.url && src.active && !officialTooLow;
  const effectivePublish = publish && canPublish;
  const why = !needsSource ? 'কমিউনিটি বা যাচাই-বাকি তথ্য প্রকাশ করা যায় না।'
    : !src ? 'প্রকাশের জন্য একটি উৎস বেছে নিন।'
    : !src.url ? 'এই উৎসের কোনো URL নেই; প্রকাশিত রেকর্ডের উৎসে URL লাগবে।'
    : officialTooLow ? 'সরকারি স্তরের জন্য আস্থা ৪–৫ এর উৎস লাগবে (সরকারি পোর্টাল, গেজেট, আদমশুমারি)।'
    : null;

  let confirm: string | undefined;
  if (effectivePublish && !current.production_eligible) confirm = 'এই রেকর্ডটি জনসাধারণের জন্য প্রকাশিত হবে। আপনি কি নিশ্চিত?';
  else if (!effectivePublish && current.production_eligible) confirm = 'এই রেকর্ডটি প্রকাশ থেকে সরিয়ে নেওয়া হবে (জনসাধারণ আর দেখবে না)। আপনি কি নিশ্চিত?';

  return (
    <ActionForm action={action} confirm={confirm} className="space-y-4">
      <Field label="প্রমাণের স্তর" en="Evidence level" htmlFor={`${idPrefix}-level`} required>
        <select id={`${idPrefix}-level`} name="evidence_level" className="input" value={level}
          onChange={(e) => { const l = e.target.value as EvidenceLevel; setLevel(l); if (!PUBLISHABLE.includes(l)) setPublish(false); }}>
          {EVIDENCE_LEVELS.map((l) => <option key={l} value={l}>{EVIDENCE_LABEL[l].bn} ({EVIDENCE_LABEL[l].en})</option>)}
        </select>
        <p className="mt-1 text-xs text-muted">{EVIDENCE_LABEL[level].hint_bn}</p>
      </Field>

      <Field label="উৎস" en="Evidence source" htmlFor={`${idPrefix}-src`} required={needsSource}>
        <select id={`${idPrefix}-src`} name="evidence_source_id" className="input" value={srcId} onChange={(e) => setSrcId(e.target.value)}>
          <option value="">— উৎস নেই —</option>
          {active.map((s) => (
            <option key={s.id} value={s.id} disabled={!s.active}>
              {s.key} · আস্থা {toBnDigits(s.trust_level)} · {s.name}{s.url ? '' : ' (URL নেই)'}{s.active ? '' : ' (নিষ্ক্রিয়)'}
            </option>
          ))}
        </select>
      </Field>
      {src && (
        <div className="rounded-chip border border-line bg-tint/50 p-3 text-xs">
          <div className="font-semibold">{src.name}</div>
          <div className="mt-1 text-muted">
            ধরন <span className="font-en">{src.source_type}</span> · আস্থা {toBnDigits(src.trust_level)}/৫
            {src.license && <> · লাইসেন্স <span className="font-en">{src.license}</span></>}
            {src.organization && <> · {src.organization}</>}
          </div>
          {src.url && <a href={src.url} target="_blank" rel="noopener noreferrer nofollow" className="font-en mt-1 block break-all text-secondary hover:underline">{src.url}</a>}
          {src.evidence_notes && <p className="mt-1">{src.evidence_notes}</p>}
        </div>
      )}
      {officialTooLow && <p className="text-xs text-danger" role="alert">সরকারি স্তরের জন্য এই উৎসের আস্থা যথেষ্ট নয় (৪–৫ লাগবে)।</p>}

      <div>
        <label className={`flex items-start gap-2 text-sm ${canPublish ? '' : 'opacity-60'}`}>
          <input type="checkbox" name="production_eligible" className="mt-1 h-4 w-4" checked={effectivePublish} disabled={!canPublish}
            onChange={(e) => setPublish(e.target.checked)} aria-describedby={`${idPrefix}-pubhint`} />
          <span>জনসাধারণের জন্য প্রকাশ করুন <span className="font-en text-xs text-muted">· production eligible</span></span>
        </label>
        <p id={`${idPrefix}-pubhint`} className="mt-1 text-xs text-muted">{why ?? 'শুধু সরকারি বা দ্বিতীয় উৎসের, URL-সহ নামযুক্ত উৎসের তথ্য প্রকাশ করা যায়।'}</p>
      </div>

      <Field label="যাচাইয়ের নোট" en="What was checked" htmlFor={`${idPrefix}-notes`} required hint="কোন নথি/পাতার সঙ্গে কী মিলিয়ে দেখা হয়েছে (৫–১০০০ অক্ষর)।">
        <textarea id={`${idPrefix}-notes`} name="verification_notes" className="input min-h-24" required minLength={5} maxLength={1000}
          defaultValue={current.verification_notes ?? ''} aria-describedby={`${idPrefix}-notes-hint`} />
      </Field>
      <SubmitButton>যাচাই সংরক্ষণ</SubmitButton>
    </ActionForm>
  );
}
