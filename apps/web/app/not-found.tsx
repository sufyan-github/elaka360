import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold">পাতাটি পাওয়া যায়নি</h1>
      <p className="mt-2 text-muted">ঠিকানাটি ভুল হতে পারে, অথবা এলাকাটি এখনো যুক্ত হয়নি।</p>
      <Link href="/explore" className="mt-6 inline-block rounded-chip bg-primary px-5 py-2.5 font-semibold text-on-primary">
        এলাকা অন্বেষণ করুন
      </Link>
    </div>
  );
}
