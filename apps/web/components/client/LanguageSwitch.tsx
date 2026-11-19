'use client';

import { Suspense } from 'react';
import NextLink from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Languages } from 'lucide-react';
import { usePathname } from '@/i18n/navigation';
import { localePath } from '@/lib/links';
import { otherLocale } from '@/lib/locale';

/**
 * A real link to this same page in the other language (path and query kept). The href is built with
 * localePath (Bangla unprefixed, English under /en) rather than next-intl's Link, which would force a `/bn` prefix.
 */
function SwitchLink({ query = '' }: { query?: string }) {
  const locale = useLocale();
  const pathname = usePathname() || '/';
  const t = useTranslations('LanguageSwitch');
  const target = otherLocale(locale);
  return (
    <NextLink
      href={localePath(target, query ? `${pathname}?${query}` : pathname)}
      prefetch={false}
      lang={target}
      hrefLang={target}
      aria-label={t('label')}
      title={t('title')}
      className="flex h-10 items-center gap-1 rounded-chip border border-line bg-surface px-2.5 text-sm font-semibold"
    >
      <Languages className="hidden h-4 w-4 sm:block" aria-hidden />
      <span className="sm:hidden" aria-hidden>{t('short')}</span>
      <span className="hidden sm:inline" aria-hidden>{t('label')}</span>
    </NextLink>
  );
}

function WithQuery() {
  return <SwitchLink query={useSearchParams().toString()} />;
}

/**
 * Header language switch. Static pages are prerendered without a query string, so the query is added on the
 * client (inside Suspense, which keeps those pages static); dynamic pages render it on the server.
 */
export function LanguageSwitch() {
  return (
    <Suspense fallback={<SwitchLink />}>
      <WithQuery />
    </Suspense>
  );
}
