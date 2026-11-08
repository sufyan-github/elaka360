import type { Metadata } from 'next';
import { NearMe } from './NearMe';

export const metadata: Metadata = { title: 'আমার আশেপাশের সেবা' };

export default async function NearMePage({ searchParams }: { searchParams: Promise<{ category?: string }> }) {
  const { category = '' } = await searchParams;
  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">আমার আশেপাশের সেবা</h1>
        <p className="text-sm text-muted">বর্তমান অবস্থানের আশেপাশে প্রয়োজনীয় প্রতিষ্ঠান ও সেবা।</p>
      </div>
      <NearMe initialCategory={category} />
    </>
  );
}
