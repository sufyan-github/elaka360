import type { Metadata } from 'next';
import { EmptyState } from '@/components/ui';

export const metadata: Metadata = { title: 'সংরক্ষিত' };

export default function SavedPage() {
  return (
    <div className="pt-6">
      <h1 className="mb-4 text-2xl font-bold">সংরক্ষিত এলাকা ও স্থান</h1>
      <EmptyState title="শীঘ্রই আসছে" body="প্রিয় স্থান সংরক্ষণ, সংগ্রহ (Collection) ও অফলাইন ডাউনলোড Phase 2-এ যুক্ত হবে।" />
    </div>
  );
}
