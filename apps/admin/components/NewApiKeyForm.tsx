'use client';

import { useActionState } from 'react';
import { createApiKey, type KeyState } from '@/app/(admin)/actions';

/** Issues a key and shows it exactly once. */
export function NewApiKeyForm() {
  const [state, action, pending] = useActionState<KeyState, FormData>(createApiKey, {});
  return (
    <form action={action} className="grid gap-3 md:grid-cols-[1fr_10rem_auto] md:items-end">
      <label className="text-sm"><span className="mb-1 block font-medium">ব্যবহারকারী/প্রকল্পের নাম</span>
        <input name="name" required minLength={3} maxLength={80} className="input" /></label>
      <label className="text-sm"><span className="mb-1 block font-medium">সীমা (অনুরোধ/মিনিট)</span>
        <input name="rate_per_min" type="number" min={1} max={6000} defaultValue={60} className="input font-en" /></label>
      <button type="submit" className="btn btn-primary" disabled={pending}>{pending ? 'অপেক্ষা করুন…' : 'কী তৈরি করুন'}</button>
      {state.error && <p role="alert" className="md:col-span-3 rounded-chip bg-danger-tint px-3 py-2 text-sm text-danger">{state.error}</p>}
      {state.key && (
        <div role="status" className="md:col-span-3 rounded-chip border border-line bg-tint p-3 text-sm">
          <p>{state.message}</p>
          <code className="mt-1 block break-all font-en text-base" aria-label="API key">{state.key}</code>
        </div>
      )}
    </form>
  );
}
