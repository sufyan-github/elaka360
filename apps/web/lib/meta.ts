import type { Metadata } from 'next';
import type { Locale } from '@elaka360/shared';
import { localePath } from './links';

/**
 * Canonical URL and hreflang alternates for a page, given its locale-less path ("/p/ruet").
 * Bangla (the default, unprefixed) is also the x-default. Relative URLs resolve against `metadataBase`.
 */
export function localeAlternates(locale: Locale, path: string): NonNullable<Metadata['alternates']> {
  return {
    canonical: localePath(locale, path),
    languages: { bn: path, en: localePath('en', path), 'x-default': path },
  };
}
