import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { asLocale } from '@/lib/locale';
import { localePath } from '@/lib/links';
import { localeAlternates } from '@/lib/meta';
import { LoginForm } from './LoginForm';

type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ next?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Login' });
  return { title: t('title'), robots: { index: false }, alternates: localeAlternates(locale, '/login') };
}

export default async function LoginPage({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Login');
  const fallback = localePath(locale, '/me');
  const next = (await searchParams).next ?? fallback;
  // Only same-site relative paths are allowed as a post-login destination (no open redirect).
  const safeNext = /^\/(?!\/)[^\s]*$/.test(next) ? next : fallback;
  return (
    <div className="mx-auto max-w-sm pt-8">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p className="mt-1 text-sm text-muted">{t('intro')}</p>
      <LoginForm next={safeNext} />
      <p className="mt-6 text-xs text-muted">{t('legal')}</p>
    </div>
  );
}
