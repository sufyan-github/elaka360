'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Star } from 'lucide-react';
import { toBnDigits } from '@elaka360/shared';

const ERRORS: Record<number, string> = {
  401: 'রিভিউ দিতে সাইন ইন করুন।',
  409: 'আপনি আগেই এই স্থানের রিভিউ দিয়েছেন। প্রোফাইল থেকে সম্পাদনা করতে পারবেন।',
  429: 'আজ আর রিভিউ দেওয়া যাবে না; পরে চেষ্টা করুন।',
};

export function ReviewForm({ slug }: { slug: string }) {
  const router = useRouter();
  const [rating, setRating] = useState(0);
  const [body, setBody] = useState('');
  const [state, setState] = useState<{ kind: 'idle' | 'busy' | 'done' | 'error'; msg?: string; status?: number }>({ kind: 'idle' });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!rating) return setState({ kind: 'error', msg: 'রেটিং বেছে নিন (১–৫)।' });
    setState({ kind: 'busy' });
    const res = await fetch(`/api/u/places/${slug}/reviews`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rating, body: body.trim() || null }),
    });
    if (res.ok) {
      setState({ kind: 'done' });
      router.refresh();
    } else setState({ kind: 'error', status: res.status, msg: ERRORS[res.status] ?? 'রিভিউ জমা দেওয়া যায়নি।' });
  }

  if (state.kind === 'done') return <p role="status" className="text-sm text-secondary">ধন্যবাদ! আপনার রিভিউ যুক্ত হয়েছে।</p>;
  return (
    <form onSubmit={submit} className="space-y-3">
      <fieldset>
        <legend className="text-sm font-medium">আপনার রেটিং</legend>
        <div className="mt-1 flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" onClick={() => setRating(n)} aria-label={`${toBnDigits(n)} তারা`} aria-pressed={rating === n}
              className="grid h-10 w-10 place-items-center rounded-chip border border-line">
              <Star className={`h-5 w-5 ${n <= rating ? 'fill-accent text-accent' : 'text-muted'}`} aria-hidden />
            </button>
          ))}
        </div>
      </fieldset>
      <label className="block text-sm">
        <span className="font-medium">মন্তব্য (ঐচ্ছিক)</span>
        <textarea value={body} onChange={(e) => setBody(e.target.value)} maxLength={2000} rows={3}
          className="mt-1 w-full rounded-chip border border-line bg-surface p-2" />
        <span className="text-xs text-muted">{toBnDigits(body.length)}/২০০০ · ব্যক্তিগত তথ্য বা কারও নাম-ফোন নম্বর লিখবেন না।</span>
      </label>
      {state.kind === 'error' && (
        <p role="alert" className="text-sm text-danger">
          {state.msg} {state.status === 401 && <Link href={`/login?next=/p/${slug}`} className="underline">সাইন ইন</Link>}
        </p>
      )}
      <button type="submit" disabled={state.kind === 'busy'} className="rounded-chip bg-primary px-4 py-2 text-sm font-semibold text-on-primary disabled:opacity-60">
        রিভিউ জমা দিন
      </button>
    </form>
  );
}
