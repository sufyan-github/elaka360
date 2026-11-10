import type { Metadata, Viewport } from 'next';
import { Hind_Siliguri, Inter } from 'next/font/google';
import Link from 'next/link';
import { Header } from '@/components/Header';
import { BottomNav } from '@/components/BottomNav';
import { ServiceWorker } from '@/components/ServiceWorker';
import './globals.css';

const hind = Hind_Siliguri({ subsets: ['bengali', 'latin'], weight: ['400', '500', '600', '700'], variable: '--font-hind-siliguri', display: 'swap' });
const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: { default: 'Elaka360 — বাংলাদেশের প্রতিটি এলাকার তথ্য', template: '%s · Elaka360' },
  description: 'বিভাগ, জেলা, প্রতিষ্ঠান, সেবা, পর্যটন ও জরুরি তথ্য — উৎসসহ, এক জায়গায়। Every Place. Every Detail.',
  applicationName: 'Elaka360',
  manifest: '/manifest.webmanifest',
  icons: { icon: [{ url: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' }], apple: '/icons/apple-touch-icon.png' },
  appleWebApp: { capable: true, title: 'Elaka360', statusBarStyle: 'default' },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [{ media: '(prefers-color-scheme: light)', color: '#075b3b' }, { media: '(prefers-color-scheme: dark)', color: '#0f1714' }],
};

/** Applies a saved theme before first paint (no flash). */
const THEME_SCRIPT = `try{var t=localStorage.getItem('e360-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="bn" className={`${hind.variable} ${inter.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-dvh">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-chip focus:bg-surface focus:px-3 focus:py-2">
          মূল বিষয়ে যান
        </a>
        <Header />
        <main id="main" className="mx-auto max-w-5xl px-4 pb-28 md:pb-12">{children}</main>
        <footer className="mx-auto max-w-5xl px-4 pb-28 text-xs text-muted md:pb-8">
          <nav aria-label="তথ্য পাতা" className="flex flex-wrap gap-x-4 gap-y-2 border-t border-line pt-4">
            <Link href="/about">আমাদের সম্পর্কে</Link>
            <Link href="/data-policy">তথ্য ও যাচাই নীতি</Link>
            <Link href="/guidelines">অবদানের নির্দেশিকা</Link>
            <Link href="/privacy">গোপনীয়তা</Link>
            <Link href="/terms">ব্যবহারের শর্তাবলি</Link>
            <Link href="/contact">যোগাযোগ</Link>
          </nav>
          <p className="mt-3">Elaka360 একটি স্বাধীন উদ্যোগ; বাংলাদেশ সরকারের সঙ্গে সম্পর্কিত নয়। জরুরি প্রয়োজনে ৯৯৯-এ কল করুন।</p>
        </footer>
        <BottomNav />
        <ServiceWorker />
      </body>
    </html>
  );
}
