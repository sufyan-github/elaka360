import Link from 'next/link';
import { Bell, Search } from 'lucide-react';

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2" aria-label="Elaka360 — হোম">
      <svg viewBox="0 0 32 40" className="h-9 w-7" aria-hidden>
        <path d="M16 0C7.2 0 0 7 0 15.7 0 27.5 16 40 16 40s16-12.5 16-24.3C32 7 24.8 0 16 0z" fill="#075b3b" />
        <path d="M16 6l9 14H7z" fill="#16865b" />
        <circle cx="16" cy="15" r="5" fill="#fff" />
      </svg>
      <span className="leading-tight">
        <span className="block font-en text-xl font-bold text-primary">Elaka360</span>
        <span className="block font-en text-[10px] text-muted">Every Place. Every Detail.</span>
      </span>
    </Link>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
        <Logo />
        <div className="flex items-center gap-2">
          <Link href="/search" className="grid h-10 w-10 place-items-center rounded-chip border border-line bg-surface" aria-label="খুঁজুন">
            <Search className="h-5 w-5" />
          </Link>
          <span className="rounded-chip border border-line bg-surface px-3 py-2 text-sm" title="English version is coming">বাংলা</span>
          <Link href="/emergency" className="hidden h-10 items-center rounded-chip bg-danger px-3 text-sm font-semibold text-white sm:flex">
            জরুরি ৯৯৯
          </Link>
          <span className="relative grid h-10 w-10 place-items-center rounded-chip border border-line bg-surface" aria-label="নোটিফিকেশন">
            <Bell className="h-5 w-5" />
          </span>
        </div>
      </div>
    </header>
  );
}
