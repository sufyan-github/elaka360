import { Search } from 'lucide-react';

export function SearchBox({ defaultValue = '', placeholder = 'এলাকা, প্রতিষ্ঠান বা সেবা খুঁজুন…', autoFocus = false }: { defaultValue?: string; placeholder?: string; autoFocus?: boolean }) {
  return (
    <form action="/search" method="get" role="search" className="flex items-center gap-2 rounded-card bg-surface p-1.5 pl-3 shadow-card">
      <Search className="h-5 w-5 shrink-0 text-muted" aria-hidden />
      <input
        name="q"
        defaultValue={defaultValue}
        placeholder={placeholder}
        aria-label="খুঁজুন"
        autoFocus={autoFocus}
        minLength={2}
        className="min-w-0 flex-1 bg-transparent py-2 text-[15px] text-ink outline-none placeholder:text-muted"
      />
      <button type="submit" className="rounded-chip bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover">
        খুঁজুন
      </button>
    </form>
  );
}
