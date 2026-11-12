import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="mx-auto max-w-md p-8 text-center">
      <h1 className="text-xl font-bold">পাতাটি পাওয়া যায়নি</h1>
      <p className="font-en mt-1 text-sm text-muted">Not found</p>
      <Link href="/" className="btn btn-outline mt-4">ড্যাশবোর্ডে ফিরুন</Link>
    </main>
  );
}
