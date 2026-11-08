import type { Metadata } from 'next';
import { EmptyState } from '@/components/ui';

export const metadata: Metadata = { title: 'প্রোফাইল' };

export default function MePage() {
  return (
    <div className="pt-6">
      <h1 className="mb-4 text-2xl font-bold">প্রোফাইল</h1>
      <EmptyState title="লগইন শীঘ্রই আসছে" body="ফোন নম্বর দিয়ে লগইন, অবদান, ব্যাজ ও লেভেল Phase 2-এ যুক্ত হবে।" />
    </div>
  );
}
