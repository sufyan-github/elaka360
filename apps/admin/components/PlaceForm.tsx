'use client';

import type { DataSource } from '@elaka360/shared';
import type { ActionState } from '@/app/(admin)/actions';
import { OWNERSHIP, OWNERSHIP_LABEL, PLACE_STATUSES, STATUS_LABEL } from '@/lib/labels';
import type { AdminPlaceRow } from '@/lib/types';
import { ActionForm, Field, SubmitButton } from './ActionForm';
import { AreaPicker } from './AreaPicker';

export interface CategoryOption { key: string; label: string; group: string }

/** Create (no `place`) or edit a place. Edits of published facts unpublish the place until re-verified (API rule). */
export function PlaceForm({ action, categories, sources, place }: {
  action: (prev: ActionState, fd: FormData) => Promise<ActionState>; categories: CategoryOption[]; sources?: DataSource[]; place?: AdminPlaceRow;
}) {
  const p = place;
  const edit = !!p;
  const groups = [...new Set(categories.map((c) => c.group))];
  const id = (k: string) => `pf-${k}`;
  return (
    <ActionForm action={action} className="space-y-4"
      confirm={edit && p.production_eligible ? 'এটি একটি প্রকাশিত স্থান। তথ্য বদলালে এটি অপ্রকাশিত হবে এবং পুনরায় যাচাই লাগবে (শুধু উৎস-নোট বদলালে নয়)। চালিয়ে যাবেন?' : undefined}>
      {edit && p.production_eligible && (
        <p className="rounded-chip border border-accent bg-tint px-3 py-2 text-sm">প্রকাশিত স্থান: নাম, ঠিকানা, ক্যাটাগরি, এলাকা বা অন্য তথ্য বদলালে প্রকাশ বাতিল হবে।</p>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="বাংলা নাম" en="name_bn" htmlFor={id('name_bn')} required>
          <input id={id('name_bn')} name="name_bn" className="input" defaultValue={p?.name_bn ?? ''} required minLength={2} maxLength={160} />
        </Field>
        <Field label="ইংরেজি নাম" en="name_en" htmlFor={id('name_en')}>
          <input id={id('name_en')} name="name_en" className="input font-en" defaultValue={p?.name_en ?? ''} minLength={2} maxLength={160} />
        </Field>
        <Field label="সংক্ষিপ্ত নাম" en="short_name" htmlFor={id('short_name')}>
          <input id={id('short_name')} name="short_name" className="input" defaultValue={p?.short_name ?? ''} maxLength={30} />
        </Field>
        <Field label="ক্যাটাগরি" en="category" htmlFor={id('category_key')} required>
          <select id={id('category_key')} name="category_key" className="input" defaultValue={p ? p.subcategory_key ?? p.category_key : ''} required={!edit}>
            <option value="">— বেছে নিন —</option>
            {groups.map((g) => (
              <optgroup key={g} label={g}>
                {categories.filter((c) => c.group === g).map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
              </optgroup>
            ))}
          </select>
        </Field>
        <Field label="মালিকানা" en="ownership" htmlFor={id('ownership')}>
          <select id={id('ownership')} name="ownership" className="input" defaultValue={p?.ownership ?? ''}>
            <option value="">— জানা নেই —</option>
            {OWNERSHIP.map((o) => <option key={o} value={o}>{OWNERSHIP_LABEL[o]} ({o})</option>)}
          </select>
        </Field>
        {edit && (
          <Field label="অবস্থা" en="status" htmlFor={id('status')}>
            <select id={id('status')} name="status" className="input" defaultValue={p.status}>
              {PLACE_STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]} ({s})</option>)}
            </select>
          </Field>
        )}
      </div>

      <AreaPicker idPrefix="pf-area" required={!edit} currentLabel={edit ? p.area_path ?? '—' : undefined} />

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="ঠিকানা (বাংলা)" en="address_bn" htmlFor={id('address_bn')}>
          <input id={id('address_bn')} name="address_bn" className="input" defaultValue={p?.address_bn ?? ''} maxLength={300} />
        </Field>
        <Field label="ঠিকানা (ইংরেজি)" en="address_en" htmlFor={id('address_en')}>
          <input id={id('address_en')} name="address_en" className="input font-en" defaultValue={p?.address_en ?? ''} maxLength={300} />
        </Field>
        <Field label="পোস্টকোড" en="postcode" htmlFor={id('postcode')}>
          <input id={id('postcode')} name="postcode" className="input font-en" defaultValue={p?.postcode ?? ''} maxLength={10} />
        </Field>
        <Field label="প্রতিষ্ঠাকাল" en="established" htmlFor={id('established')}>
          <input id={id('established')} name="established" className="input font-en" defaultValue={p?.established ?? ''} maxLength={30} />
        </Field>
        <Field label="অক্ষাংশ" en="lat (20.3–26.8)" htmlFor={id('lat')}>
          <input id={id('lat')} name="lat" type="number" step="any" min={20.3} max={26.8} className="input font-en" defaultValue={p?.lat ?? ''} />
        </Field>
        <Field label="দ্রাঘিমাংশ" en="lon (88–92.8)" htmlFor={id('lon')}>
          <input id={id('lon')} name="lon" type="number" step="any" min={88} max={92.8} className="input font-en" defaultValue={p?.lon ?? ''} />
        </Field>
        <Field label="ফোন নম্বর" en="phones, comma separated (≤6)" htmlFor={id('phones')}>
          <input id={id('phones')} name="phones" className="input font-en" defaultValue={p?.phones?.join(', ') ?? ''} />
        </Field>
        <Field label="ইমেইল" en="email" htmlFor={id('email')}>
          <input id={id('email')} name="email" type="email" className="input font-en" defaultValue={p?.email ?? ''} maxLength={120} />
        </Field>
        <Field label="ওয়েবসাইট" en="website" htmlFor={id('website')} className="md:col-span-2">
          <input id={id('website')} name="website" type="url" className="input font-en" defaultValue={p?.website ?? ''} maxLength={300} />
        </Field>
        <Field label="বিবরণ (বাংলা)" en="description_bn" htmlFor={id('description_bn')}>
          <textarea id={id('description_bn')} name="description_bn" className="input min-h-20" defaultValue={p?.description_bn ?? ''} maxLength={2000} />
        </Field>
        <Field label="বিবরণ (ইংরেজি)" en="description_en" htmlFor={id('description_en')}>
          <textarea id={id('description_en')} name="description_en" className="input min-h-20 font-en" defaultValue={p?.description_en ?? ''} maxLength={2000} />
        </Field>
        {!edit && sources && (
          <Field label="ডেটা উৎস" en="data_source_id" htmlFor={id('data_source_id')}>
            <select id={id('data_source_id')} name="data_source_id" className="input" defaultValue="">
              <option value="">— নেই —</option>
              {sources.filter((s) => s.active).map((s) => <option key={s.id} value={s.id}>{s.key} · {s.name}</option>)}
            </select>
          </Field>
        )}
        <Field label="উৎস-নোট" en="source_notes" htmlFor={id('source_notes')}>
          <textarea id={id('source_notes')} name="source_notes" className="input min-h-20" defaultValue={p?.source_notes ?? ''} maxLength={1000} />
        </Field>
      </div>
      {!edit && <p className="text-xs text-muted">নতুন স্থান অযাচাইকৃত ও অপ্রকাশিত অবস্থায় তৈরি হয়; প্রকাশের জন্য যাচাই ফর্ম ব্যবহার করুন।</p>}
      {edit && (
        <Field label="পরিবর্তনের কারণ" en="reason (required, ≥5)" htmlFor={id('reason')} required hint="অডিট লগে সংরক্ষিত হবে।">
          <input id={id('reason')} name="reason" className="input" required minLength={5} maxLength={500} aria-describedby={`${id('reason')}-hint`} />
        </Field>
      )}
      <SubmitButton>{edit ? 'পরিবর্তন সংরক্ষণ' : 'স্থান তৈরি করুন'}</SubmitButton>
    </ActionForm>
  );
}
