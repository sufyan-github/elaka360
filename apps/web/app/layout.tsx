import type { Metadata, Viewport } from 'next';
import { Hind_Siliguri, Inter } from 'next/font/google';
import { Header } from '@/components/Header';
import { BottomNav } from '@/components/BottomNav';
import './globals.css';

const hind = Hind_Siliguri({ subsets: ['bengali', 'latin'], weight: ['400', '500', '600', '700'], variable: '--font-hind-siliguri', display: 'swap' });
const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: { default: 'Elaka360 — বাংলাদেশের প্রতিটি এলাকার সব তথ্য', template: '%s · Elaka360' },
  description: 'জেলা, উপজেলা, ইউনিয়ন, প্রতিষ্ঠান, সেবা, পর্যটন ও জরুরি তথ্য — এক জায়গায়। Every Place. Every Detail.',
  applicationName: 'Elaka360',
};

export const viewport: Viewport = { themeColor: '#075b3b', width: 'device-width', initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="bn" className={`${hind.variable} ${inter.variable}`}>
      <body className="min-h-dvh">
        <Header />
        <main className="mx-auto max-w-5xl px-4 pb-28 md:pb-12">{children}</main>
        <BottomNav />
      </body>
    </html>
  );
}
