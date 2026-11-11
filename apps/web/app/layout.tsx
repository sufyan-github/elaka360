/**
 * Pass-through root layout. The real document (<html lang>, header, footer) is app/[locale]/layout.tsx;
 * this file only exists so that app/not-found.tsx can render for requests outside a locale.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
