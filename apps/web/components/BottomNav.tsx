'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bookmark, Home, Map, Search, User } from 'lucide-react';

const TABS = [
  { href: '/', label: 'হোম', Icon: Home },
  { href: '/explore', label: 'অন্বেষণ', Icon: Map },
  { href: '/search', label: 'খুঁজুন', Icon: Search, center: true },
  { href: '/saved', label: 'সংরক্ষিত', Icon: Bookmark },
  { href: '/me', label: 'প্রোফাইল', Icon: User },
] as const;

const NON_AREA = ['/search', '/saved', '/me', '/emergency', '/near-me', '/login', '/contribute', '/map', '/p/', '/c/', '/about', '/contact', '/privacy', '/terms', '/data-policy', '/guidelines', '/offline'];

function isActive(pathname: string, href: string) {
  if (href === '/') return pathname === '/';
  if (href === '/explore') return pathname === '/explore' || (!NON_AREA.some((p) => pathname.startsWith(p)) && pathname !== '/');
  return pathname.startsWith(href);
}

export function BottomNav() {
  const pathname = usePathname() ?? '/';
  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] md:hidden" aria-label="প্রধান">
      <ul className="mx-auto grid max-w-md grid-cols-5">
        {TABS.map(({ href, label, Icon, ...rest }) => {
          const active = isActive(pathname, href);
          const center = 'center' in rest;
          return (
            <li key={href}>
              <Link href={href} className="flex flex-col items-center gap-0.5 py-2 text-xs" aria-current={active ? 'page' : undefined}>
                {center ? (
                  <span className="-mt-6 grid h-12 w-12 place-items-center rounded-full bg-primary text-on-primary shadow-card">
                    <Icon className="h-6 w-6" aria-hidden />
                  </span>
                ) : (
                  <span className={`grid h-8 w-12 place-items-center rounded-full ${active ? 'bg-tint text-primary' : 'text-ink'}`}>
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                )}
                <span className={active ? 'font-semibold text-primary' : 'text-ink'}>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
