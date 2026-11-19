'use client';

export default function AdminError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div role="alert" className="rounded-card border border-danger/30 bg-danger-tint p-5">
      <h1 className="text-lg font-bold text-danger">কিছু একটা ভুল হয়েছে</h1>
      <p className="mt-1 text-sm">{error.message || 'Unexpected error'}</p>
      {error.digest && <p className="font-en mt-1 text-xs text-muted">digest: {error.digest}</p>}
      <button type="button" onClick={reset} className="btn btn-outline mt-4">আবার চেষ্টা করুন</button>
    </div>
  );
}
