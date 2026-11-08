import type { Metadata } from 'next';
import { MapExplorer } from './MapExplorer';

export const metadata: Metadata = { title: 'মানচিত্রে বাংলাদেশ' };

export default function MapPage() {
  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">মানচিত্রে বাংলাদেশ</h1>
        <p className="text-sm text-muted">বিভাগ, জেলা ও গুরুত্বপূর্ণ প্রতিষ্ঠান — ইন্টারঅ্যাক্টিভ মানচিত্রে।</p>
      </div>
      <MapExplorer />
    </>
  );
}
