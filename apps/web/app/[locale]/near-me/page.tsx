import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { NearMe } from './NearMe';

type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ category?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'NearMe' });
  return { title: t('title'), alternates: localeAlternates(locale, '/near-me') };
}

export default async function NearMePage({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('NearMe');
  const { category = '' } = await searchParams;
  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <p className="text-sm text-muted">{t('subtitle')}</p>
      </div>
      <NearMe initialCategory={category} />
    </>
  );
}
