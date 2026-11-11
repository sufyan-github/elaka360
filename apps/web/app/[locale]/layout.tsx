import type { Metadata, Viewport } from 'next';
import { notFound } from 'next/navigation';
import { Hind_Siliguri, Inter } from 'next/font/google';
import { hasLocale, NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslations, setRequestLocale } from 'next-intl/server';
import { routing } from '@/i18n/routing';
import { Link } from '@/i18n/navigation';
import { Header } from '@/components/Header';
import { BottomNav } from '@/components/BottomNav';
import { ServiceWorker } from '@/components/ServiceWorker';
import '../globals.css';

const hind = Hind_Siliguri({ subsets: ['bengali', 'latin'], weight: ['400', '500', '600', '700'], variable: '--font-hind-siliguri', display: 'swap' });
const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' });

/** Both locales are known at build time, so static and ISR pages stay static per locale. */
export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

type Props = { children: React.ReactNode; params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale: hasLocale(routing.locales, locale) ? locale : routing.defaultLocale, namespace: 'Meta' });
  return {
    metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
    title: { default: t('title'), template: '%s · Elaka360' },
    description: t('description'),
    applicationName: 'Elaka360',
    manifest: '/manifest.webmanifest',
    icons: { icon: [{ url: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' }], apple: '/icons/apple-touch-icon.png' },
    appleWebApp: { capable: true, title: 'Elaka360', statusBarStyle: 'default' },
  };
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [{ media: '(prefers-color-scheme: light)', color: '#075b3b' }, { media: '(prefers-color-scheme: dark)', color: '#0f1714' }],
};

/** Applies a saved theme before first paint (no flash). */
const THEME_SCRIPT = `try{var t=localStorage.getItem('e360-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}`;

/** Message namespaces used by client components; the long static-page texts stay on the server. */
const CLIENT_NAMESPACES = [
  'Common', 'Evidence', 'LanguageSwitch', 'BottomNav', 'Theme', 'SearchBox', 'ServiceWorker', 'Map', 'MapExplorer', 'NearMe',
  'Wizard', 'Login', 'Account', 'Review', 'SaveShare', 'ContactForm', 'Error',
] as const;

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const [t, messages] = await Promise.all([getTranslations('Layout'), getMessages()]);
  const clientMessages = Object.fromEntries(CLIENT_NAMESPACES.map((ns) => [ns, messages[ns]]));

  return (
    <html lang={locale} className={`${hind.variable} ${inter.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-dvh">
        <NextIntlClientProvider locale={locale} messages={clientMessages} timeZone="Asia/Dhaka">
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-chip focus:bg-surface focus:px-3 focus:py-2">
            {t('skipToContent')}
          </a>
          <Header />
          <main id="main" className="mx-auto max-w-5xl px-4 pb-28 md:pb-12">{children}</main>
          <footer className="mx-auto max-w-5xl px-4 pb-28 text-xs text-muted md:pb-8">
            <nav aria-label={t('footerNav')} className="flex flex-wrap gap-x-4 gap-y-2 border-t border-line pt-4">
              <Link href="/about">{t('about')}</Link>
              <Link href="/data-policy">{t('dataPolicy')}</Link>
              <Link href="/guidelines">{t('guidelines')}</Link>
              <Link href="/privacy">{t('privacy')}</Link>
              <Link href="/terms">{t('terms')}</Link>
              <Link href="/contact">{t('contact')}</Link>
            </nav>
            <p className="mt-3">{t('disclaimer')}</p>
          </footer>
          <BottomNav />
          <ServiceWorker />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
