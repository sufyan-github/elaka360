import type { Metadata, Viewport } from 'next';
import { Hind_Siliguri, Inter } from 'next/font/google';
import './globals.css';

const hind = Hind_Siliguri({ subsets: ['bengali', 'latin'], weight: ['400', '500', '600', '700'], variable: '--font-hind-siliguri', display: 'swap' });
const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' });

export const metadata: Metadata = {
  title: { default: 'Elaka360 অ্যাডমিন', template: '%s · Elaka360 অ্যাডমিন' },
  description: 'Elaka360 কর্মীদের জন্য যাচাই, মডারেশন ও ডেটা ব্যবস্থাপনা।',
  applicationName: 'Elaka360 Admin',
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { themeColor: '#075b3b', width: 'device-width', initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="bn" className={`${hind.variable} ${inter.variable}`}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
