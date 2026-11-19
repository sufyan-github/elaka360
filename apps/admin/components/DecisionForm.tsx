'use client';

import type { ContributionStatus, ContributionType } from '@elaka360/shared';
import type { ActionState } from '@/app/(admin)/actions';
import { NEW_PLACE_TYPES } from '@/lib/labels';
import { ActionForm, Field, SubmitButton } from './ActionForm';
import { AreaPicker } from './AreaPicker';

const ALLOWED: Record<string, ContributionStatus[]> = {
  start_review: ['new'], approve: ['new', 'in_review'], request_changes: ['new', 'in_review'], reject: ['new', 'in_review', 'needs_changes'],
};

/** Moderation decision. A note is required (except start_review); approving a new-place type needs an area. */
export function DecisionForm({ action, status, type, suggestedAreaId }: {
  action: (prev: ActionState, fd: FormData) => Promise<ActionState>; status: ContributionStatus; type: ContributionType; suggestedAreaId: number | null;
}) {
  const can = (d: string) => ALLOWED[d]!.includes(status);
  const newPlace = NEW_PLACE_TYPES.includes(type);
  if (!Object.keys(ALLOWED).some(can)) {
    return <p className="text-sm text-muted">এই অবদানের সিদ্ধান্ত হয়ে গেছে; আর কোনো পদক্ষেপ নেই।</p>;
  }
  return (
    <ActionForm action={action} className="space-y-4">
      <input type="hidden" name="type" value={type} />
      <Field label="সিদ্ধান্তের নোট" en="note (required except start review; sent to the contributor)" htmlFor="d-note">
        <textarea id="d-note" name="note" className="input min-h-24" maxLength={1000} />
      </Field>
      {newPlace && can('approve') && (
        <div>
          <AreaPicker idPrefix="d-area" required defaultRaw={suggestedAreaId ? String(suggestedAreaId) : ''} />
          <p className="mt-1 text-xs text-muted">অনুমোদন করলে একটি অপ্রকাশিত স্থান তৈরি হবে (প্রমাণ: কমিউনিটি)। প্রকাশের জন্য পরে যাচাই লাগবে।</p>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {can('start_review') && <SubmitButton variant="outline" name="decision" value="start_review">পর্যালোচনা শুরু · Start review</SubmitButton>}
        {can('approve') && (
          <SubmitButton name="decision" value="approve"
            confirm={newPlace ? 'অনুমোদন করলে নির্বাচিত এলাকায় একটি নতুন (অপ্রকাশিত) স্থান তৈরি হবে। নিশ্চিত?' : 'এই অবদান অনুমোদন করবেন?'}>
            অনুমোদন · Approve
          </SubmitButton>
        )}
        {can('request_changes') && <SubmitButton variant="outline" name="decision" value="request_changes" confirm="অবদানকারীকে সংশোধনের অনুরোধ পাঠানো হবে। নিশ্চিত?">সংশোধন চাই · Request changes</SubmitButton>}
        {can('reject') && <SubmitButton variant="danger" name="decision" value="reject" confirm="এই অবদান বাতিল করা হবে এবং অবদানকারীকে জানানো হবে। এটি ফেরানো যাবে না। নিশ্চিত?">বাতিল · Reject</SubmitButton>}
      </div>
    </ActionForm>
  );
}
