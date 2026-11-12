export default function Loading() {
  return (
    <div role="status" aria-live="polite" className="space-y-4">
      <span className="sr-only">লোড হচ্ছে…</span>
      <div className="h-8 w-56 animate-pulse rounded-chip bg-tint" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Array.from({ length: 8 }, (_, i) => <div key={i} className="h-24 animate-pulse rounded-card bg-tint" />)}
      </div>
      <div className="h-64 animate-pulse rounded-card bg-tint" />
    </div>
  );
}
