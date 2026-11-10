'use client';

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold">কিছু একটা সমস্যা হয়েছে</h1>
      <p className="mt-2 text-muted">সার্ভারের সাথে সংযোগ করা যায়নি। একটু পরে আবার চেষ্টা করুন।</p>
      <button onClick={reset} className="mt-6 rounded-chip bg-primary px-5 py-2.5 font-semibold text-on-primary">
        আবার চেষ্টা করুন
      </button>
    </div>
  );
}
