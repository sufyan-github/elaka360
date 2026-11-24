#!/usr/bin/env node
// Bundle the MapLibre complex-text plugin (apps/web/vendor/maplibre-complex-text) into one worker script:
// apps/web/public/maplibre/complex-text.js. The output is committed; rebuild only when the vendor folder changes.
// Usage: node scripts/build-complex-text.mjs
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'apps', 'web', 'vendor', 'maplibre-complex-text');
const out = join(ROOT, 'apps', 'web', 'public', 'maplibre', 'complex-text.js');
// esbuild is not a direct dependency: use the copy wrangler (apps/edge-api) already installs
const fromEdge = createRequire(join(ROOT, 'apps', 'edge-api', 'package.json'));
const { build } = createRequire(fromEdge.resolve('wrangler/package.json'))('esbuild');

await build({
  entryPoints: [join(SRC, 'index.js')],
  outfile: out,
  bundle: true,
  format: 'iife',
  minify: true,
  target: 'es2020',
  loader: { '.wasm': 'binary', '.txt': 'text', '.csv': 'text' },
  banner: { js: '/* MapLibre complex text (Bangla) — from wipfli/maplibre-gl-complex-text (MIT), HarfBuzz (MIT), Noto fonts (OFL). See apps/web/vendor/maplibre-complex-text/README.md */' },
  logLevel: 'info',
});
