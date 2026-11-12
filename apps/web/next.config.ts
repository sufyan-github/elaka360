import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const MAP_ORIGIN = (() => {
  try {
    return new URL(process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/positron').origin;
  } catch {
    return 'https://tiles.openfreemap.org';
  }
})();

// Next.js injects inline bootstrap scripts, so script-src needs 'unsafe-inline' without a nonce setup.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'" + (process.env.NODE_ENV === 'development' ? " 'unsafe-eval'" : ''),
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${MAP_ORIGIN}`,
  "font-src 'self' data:",
  `connect-src 'self' ${MAP_ORIGIN}`,
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join('; ');

const nextConfig: NextConfig = {
  // NEXT_DIST_DIR lets a second build (e.g. a preview next to `next dev`) use its own folder instead of clobbering .next
  distDir: process.env.NEXT_DIST_DIR || '.next',
  reactStrictMode: true,
  poweredByHeader: false,
  eslint: { ignoreDuringBuilds: true }, // linted separately by `pnpm lint` (eslint.config.mjs at the repo root)
  /**
   * Bangla (default locale) URLs have no prefix: `/x` is served by app/[locale] as `/bn/x`. This is a config
   * rewrite, not a middleware rewrite, because Next.js matches ISR routes against the rewritten path only for
   * config rewrites (with a middleware rewrite, `/p/ruet` and `/rajshahi` were rendered dynamically on every
   * request). Applied after files and static routes, so public files, `/manifest.webmanifest` and `/api/*`
   * never reach it; `/en/*` and `/bn/*` are excluded (the middleware redirects `/bn/x` to `/x`).
   */
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [
        { source: '/', destination: '/bn' },
        { source: '/:path((?!en(?:/|$)|bn(?:/|$)|api(?:/|$)|_next(?:/|$)).+)', destination: '/bn/:path' },
      ],
      fallback: [],
    };
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Content-Security-Policy', value: CSP },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'geolocation=(self), camera=(), microphone=()' },
          { key: 'X-Frame-Options', value: 'DENY' },
        ],
      },
      { source: '/sw.js', headers: [{ key: 'Cache-Control', value: 'no-cache' }, { key: 'Service-Worker-Allowed', value: '/' }] },
    ];
  },
};

export default withNextIntl(nextConfig);
