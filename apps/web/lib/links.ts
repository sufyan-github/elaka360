/** URL helpers safe to use in both server and client components. */
import type { Locale } from '@elaka360/shared';

/** URL of an area page in the web app (without a locale prefix). The country lives at /explore. */
export function areaHref(a: { path: string; level: string }): string {
  return a.level === 'country' ? '/explore' : `/${a.path}`;
}

/**
 * Put a locale-less app path ("/p/ruet", "/login?next=…") into the given locale: Bangla is unprefixed,
 * English lives under /en. Use it where a plain string URL is needed (DOM links, `next=` targets, metadata);
 * components should prefer `Link` from '@/i18n/navigation', which does this automatically.
 */
export function localePath(locale: Locale, path: string): string {
  if (locale === 'bn') return path;
  if (path === '/' || path === '') return '/en';
  if (path.startsWith('/?') || path.startsWith('/#')) return `/en${path.slice(1)}`;
  return `/en${path}`;
}
