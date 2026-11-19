import { defineRouting } from 'next-intl/routing';

/**
 * Bangla is the default and lives at `/` (URLs unchanged); English lives under `/en/...`.
 * No Accept-Language detection and no locale cookie: a URL always means the same language, so pages stay
 * cacheable (ISR/static) and `/` never redirects. The language switch in the header links between the two.
 */
export const routing = defineRouting({
  locales: ['bn', 'en'],
  defaultLocale: 'bn',
  localePrefix: 'as-needed',
  localeDetection: false,
  localeCookie: false,
  // hreflang alternates are emitted in each page's metadata instead of a `Link` response header.
  alternateLinks: false,
});

export type AppLocale = (typeof routing.locales)[number];
