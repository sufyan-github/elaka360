import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { MapExplorer } from './MapExplorer';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'MapPage' });
  return { title: t('title'), alternates: localeAlternates(locale, '/map') };
}

export default async function MapPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('MapPage');
  return (
    <>
      <div className="pt-6">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <p className="text-sm text-muted">{t('subtitle')}</p>
      </div>
      <MapExplorer />
    </>
  );
}
