'use client';

import { useTranslations } from 'next-intl';

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations('Error');
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p className="mt-2 text-muted">{t('body')}</p>
      <button onClick={reset} className="mt-6 rounded-chip bg-primary px-5 py-2.5 font-semibold text-on-primary">
        {t('retry')}
      </button>
    </div>
  );
}
