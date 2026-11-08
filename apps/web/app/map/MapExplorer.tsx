'use client';

import { useState } from 'react';
import { MapView } from '@/components/map/MapView';

const CATS = [
  { key: '', label: 'সব' }, { key: 'education', label: 'শিক্ষা' }, { key: 'health', label: 'স্বাস্থ্য' },
  { key: 'government', label: 'সরকারি' }, { key: 'tourism', label: 'পর্যটন' }, { key: 'religious', label: 'ধর্মীয়' },
  { key: 'emergency', label: 'জরুরি' }, { key: 'transport', label: 'পরিবহন' },
];

export function MapExplorer() {
  const [category, setCategory] = useState('');
  return (
    <>
      <div className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
        {CATS.map((c) => (
          <button key={c.key} onClick={() => setCategory(c.key)} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${category === c.key ? 'bg-primary text-white' : 'border border-line bg-surface'}`}>
            {c.label}
          </button>
        ))}
      </div>
      <MapView category={category || undefined} className="mt-3 h-[70dvh]" />
      <p className="mt-2 text-xs text-muted">জেলায় চাপ দিলে জেলার পাতা খুলবে। পাইলট পর্যায়ে শুধু রাজশাহীর যাচাইকৃত স্থান দেখানো হচ্ছে।</p>
    </>
  );
}
