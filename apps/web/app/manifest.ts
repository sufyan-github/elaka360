import type { MetadataRoute } from 'next';

/** Web app manifest, served by Next at /manifest.webmanifest. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: 'Elaka360 — এলাকা৩৬০',
    short_name: 'Elaka360',
    description: 'বাংলাদেশের এলাকাভিত্তিক তথ্য — জেলা, উপজেলা, প্রতিষ্ঠান, সেবা ও জরুরি নম্বর, উৎসসহ।',
    lang: 'bn',
    dir: 'ltr',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    theme_color: '#075b3b',
    background_color: '#f7f9f6',
    categories: ['navigation', 'utilities', 'travel'],
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
    shortcuts: [
      {
        name: 'জরুরি ৯৯৯',
        short_name: 'জরুরি',
        description: 'জরুরি সেবা ও হটলাইন নম্বর',
        url: '/emergency',
        icons: [{ src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' }],
      },
    ],
  };
}
