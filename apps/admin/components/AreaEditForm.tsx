'use client';

import { useState } from 'react';
import type { ActionState } from '@/app/(admin)/actions';
import { AREA_STATUSES, STATUS_LABEL } from '@/lib/labels';
import type { AdminAreaRow } from '@/lib/types';
import { ActionForm, Field, SubmitButton } from './ActionForm';

export function AreaEditForm({ action, area }: { action: (prev: ActionState, fd: FormData) => Promise<ActionState>; area: AdminAreaRow }) {
  const [nameBn, setNameBn] = useState(area.name_bn);
  const [nameEn, setNameEn] = useState(area.name_en);
  const [status, setStatus] = useState(area.status);
  const [parent, setParent] = useState('');
  const renamed = nameBn.trim() !== area.name_bn || nameEn.trim() !== area.name_en;
  const unpublishes = renamed && area.production_eligible;

  const confirm = unpublishes ? 'নাম বদলালে এই প্রকাশিত এলাকাটি অপ্রকাশিত হবে এবং পুনরায় যাচাই লাগবে। চালিয়ে যাবেন?'
    : status !== area.status && status !== 'active' ? `অবস্থা "${STATUS_LABEL[status] ?? status}" করা হবে। নিশ্চিত?`
    : parent ? 'অভিভাবক বদলালে এই এলাকা ও তার নিচের সব এলাকার পাথ (URL) বদলে যাবে। নিশ্চিত?'
    : undefined;

  return (
    <ActionForm action={action} confirm={confirm} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="বাংলা নাম" en="name_bn" htmlFor="a-name_bn" required>
          <input id="a-name_bn" name="name_bn" className="input" value={nameBn} onChange={(e) => setNameBn(e.target.value)} required minLength={2} maxLength={120} />
        </Field>
        <Field label="ইংরেজি নাম" en="name_en" htmlFor="a-name_en" required>
          <input id="a-name_en" name="name_en" className="input font-en" value={nameEn} onChange={(e) => setNameEn(e.target.value)} required minLength={2} maxLength={120} />
        </Field>
        <Field label="বিবিএস কোড" en="bbs_code" htmlFor="a-bbs">
          <input id="a-bbs" name="bbs_code" className="input font-en" defaultValue={area.bbs_code ?? ''} maxLength={20} />
        </Field>
        <Field label="ওয়েবসাইট" en="website" htmlFor="a-web">
          <input id="a-web" name="website" type="url" className="input font-en" defaultValue={area.website ?? ''} maxLength={300} />
        </Field>
        <Field label="অক্ষাংশ" en="lat (20.3–26.8)" htmlFor="a-lat">
          <input id="a-lat" name="lat" type="number" step="any" min={20.3} max={26.8} className="input font-en" defaultValue={area.lat ?? ''} />
        </Field>
        <Field label="দ্রাঘিমাংশ" en="lon (88–92.8)" htmlFor="a-lon">
          <input id="a-lon" name="lon" type="number" step="any" min={88} max={92.8} className="input font-en" defaultValue={area.lon ?? ''} />
        </Field>
        <Field label="অবস্থা" en="status" htmlFor="a-status">
          <select id="a-status" name="status" className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            {AREA_STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]} ({s})</option>)}
          </select>
        </Field>
        <Field label="নতুন অভিভাবক এলাকার আইডি" en="parent_id (move)" htmlFor="a-parent" hint={`বর্তমান: #${area.parent_id ?? '—'}। খালি রাখলে বদলাবে না।`}>
          <input id="a-parent" name="parent_id" inputMode="numeric" pattern="[0-9]*" className="input font-en" value={parent} onChange={(e) => setParent(e.target.value.trim())} aria-describedby="a-parent-hint" />
        </Field>
      </div>
      <Field label="নোট" en="notes" htmlFor="a-notes">
        <textarea id="a-notes" name="notes" className="input min-h-20" defaultValue={area.notes ?? ''} maxLength={2000} />
      </Field>
      {unpublishes && (
        <p role="alert" className="rounded-chip border border-accent bg-tint px-3 py-2 text-sm">
          নাম বদলালে প্রকাশিত তথ্য বদলায়: এলাকাটি অপ্রকাশিত হবে এবং প্রমাণের স্তর “যাচাই বাকি” হবে।
        </p>
      )}
      <Field label="পরিবর্তনের কারণ" en="reason (required, ≥5)" htmlFor="a-reason" required hint="অডিট লগে সংরক্ষিত হবে।">
        <input id="a-reason" name="reason" className="input" required minLength={5} maxLength={500} aria-describedby="a-reason-hint" />
      </Field>
      <SubmitButton>পরিবর্তন সংরক্ষণ</SubmitButton>
    </ActionForm>
  );
}
