'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';
import {
  BookMarked, ClipboardCheck, Copy, KeyRound, Flag, History, LayoutDashboard, LogOut, MapPinned, Menu, MessageSquareWarning, Shield, Store, Users, X,
} from 'lucide-react';
import type { NavItem } from '@/lib/nav';

const ICONS: Record<string, typeof Menu> = {
  dashboard: LayoutDashboard, verify: ClipboardCheck, areas: MapPinned, places: Store, moderation: MessageSquareWarning,
  reports: Flag, sources: BookMarked, audit: History, users: Users, duplicates: Copy, keys: KeyRound,
};

export function Shell({ nav, user, children }: { nav: NavItem[]; user: { name: string; role: string; roleEn: string; scope: string | null }; children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const active = (href: string) => (href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`));

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-chip focus:bg-surface focus:px-3 focus:py-2">মূল অংশে যান</a>
      {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setOpen(false)} aria-hidden />}
      <aside id="sidebar"
        className={`fixed inset-y-0 left-0 z-40 w-60 transform border-r border-line bg-surface transition-transform lg:sticky lg:top-0 lg:h-dvh lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex h-14 items-center justify-between border-b border-line px-4">
          <Link href="/" className="flex items-center gap-2 font-bold text-primary">
            <Shield className="h-5 w-5" aria-hidden /> Elaka360 <span className="font-normal text-muted">অ্যাডমিন</span>
          </Link>
          <button type="button" className="btn btn-outline btn-sm lg:hidden" onClick={() => setOpen(false)} aria-label="মেনু বন্ধ করুন">
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav aria-label="প্রধান মেনু" className="overflow-y-auto p-2">
          <ul className="space-y-0.5">
            {nav.map((n) => {
              const Icon = ICONS[n.icon] ?? LayoutDashboard;
              const on = active(n.href);
              return (
                <li key={n.href}>
                  <Link href={n.href} aria-current={on ? 'page' : undefined}
                    className={`flex items-center gap-3 rounded-chip px-3 py-2 text-sm ${on ? 'bg-tint font-semibold text-primary' : 'text-ink hover:bg-tint'}`}>
                    <Icon className="h-4 w-4 shrink-0" aria-hidden />
                    <span className="flex-1">{n.bn}</span>
                    <span className="font-en text-[10px] text-muted">{n.en}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-surface/95 px-4 backdrop-blur">
          <button type="button" className="btn btn-outline btn-sm lg:hidden" onClick={() => setOpen(true)} aria-label="মেনু খুলুন" aria-expanded={open} aria-controls="sidebar">
            <Menu className="h-4 w-4" />
          </button>
          <div className="flex-1" />
          <div className="text-right text-sm leading-tight">
            <div className="font-semibold">{user.name}</div>
            <div className="text-xs text-muted">{user.role} <span className="font-en">· {user.roleEn}</span>{user.scope && <> · <span className="font-en">{user.scope}</span></>}</div>
          </div>
          <form method="post" action="/api/auth/logout">
            <button type="submit" className="btn btn-outline btn-sm" title="সাইন আউট">
              <LogOut className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">সাইন আউট</span>
            </button>
          </form>
        </header>
        <main id="main" className="mx-auto max-w-7xl px-4 py-6 lg:px-6">{children}</main>
      </div>
    </div>
  );
}
