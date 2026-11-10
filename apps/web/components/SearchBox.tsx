'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';

interface Suggestion { kind: 'area' | 'place'; name_bn: string; name_en: string; href_key: string; detail: string }

/** Search box with keyboard-accessible suggestions (combobox pattern). Stale requests are aborted. */
export function SearchBox({ defaultValue = '', autoFocus = false }: { defaultValue?: string; autoFocus?: boolean }) {
  const router = useRouter();
  const [q, setQ] = useState(defaultValue);
  const [items, setItems] = useState<Suggestion[]>([]);
  const [active, setActive] = useState(-1);
  const [open, setOpen] = useState(false);
  const listId = useId();
  const ctrl = useRef<AbortController | null>(null);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) { setItems([]); return; }
    const t = setTimeout(() => {
      ctrl.current?.abort();
      ctrl.current = new AbortController();
      fetch(`/api/suggest?q=${encodeURIComponent(term)}`, { signal: ctrl.current.signal })
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .then((d: { items: Suggestion[] }) => { setItems(d.items.slice(0, 8)); setActive(-1); })
        .catch(() => undefined);
    }, 180);
    return () => clearTimeout(t);
  }, [q]);

  const href = (s: Suggestion) => (s.kind === 'area' ? `/${s.href_key}` : `/p/${s.href_key}`);

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        if (active >= 0 && items[active]) router.push(href(items[active]!));
        else if (q.trim()) router.push(`/search?q=${encodeURIComponent(q.trim())}`);
        setOpen(false);
      }}
      className="relative"
    >
      <div className="flex items-center gap-2 rounded-card border border-line bg-surface p-1.5 pl-3 shadow-card">
        <Search className="h-5 w-5 shrink-0 text-muted" aria-hidden />
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)); }
            if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, -1)); }
            if (e.key === 'Escape') setOpen(false);
          }}
          autoFocus={autoFocus}
          name="q"
          type="search"
          maxLength={80}
          placeholder="জেলা, উপজেলা, প্রতিষ্ঠান বা সেবা খুঁজুন…"
          aria-label="খুঁজুন"
          role="combobox"
          aria-expanded={open && items.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          className="min-w-0 flex-1 bg-transparent py-2 text-[15px] outline-none placeholder:text-muted"
        />
        <button type="submit" className="rounded-chip bg-primary px-4 py-2 text-sm font-semibold text-on-primary hover:bg-primary-hover">
          খুঁজুন
        </button>
      </div>
      {open && items.length > 0 && (
        <ul id={listId} role="listbox" className="absolute inset-x-0 top-full z-20 mt-1 overflow-hidden rounded-card border border-line bg-surface text-ink shadow-card">
          {items.map((s, i) => (
            <li key={`${s.kind}-${s.href_key}`} id={`${listId}-${i}`} role="option" aria-selected={i === active}>
              <a href={href(s)} onMouseDown={(e) => { e.preventDefault(); router.push(href(s)); setOpen(false); }}
                 className={`flex items-center justify-between gap-2 px-3 py-2 text-sm ${i === active ? 'bg-tint' : ''}`}>
                <span className="truncate">{s.name_bn} <span className="font-en text-xs text-muted">{s.name_en}</span></span>
                <span className="shrink-0 text-xs text-muted">{s.kind === 'area' ? 'এলাকা' : 'স্থান'}</span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
