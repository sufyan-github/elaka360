#!/usr/bin/env node
// Run after `opennextjs-cloudflare build` (apps/web `cf:build`).
//
// Next.js de-duplicates page renders with a Batcher: a module-level map from page to the promise of the render in
// progress, shared by every request in the isolate. On Cloudflare Workers a promise can only settle in the request that
// created it. When that request is cancelled (a visitor leaves, or the free plan's CPU limit stops it), its entry is
// never removed, and every later request for the same page awaits it and fails at once ("This promise was created by a
// request that has since ended"): /khulna, /rajshahi or a place page then returns 500 until the isolate is replaced.
// Same bug class as withastro/astro#18764 and TanStack/router#8951.
//
// This patch turns the de-duplication off in the built server: each request renders (or reads the cache) itself.
// It edits only .open-next/server-functions, fails if it finds no batcher, and is safe to run twice.
import { lstatSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = join(process.cwd(), '.open-next', 'server-functions');
// minified: let n=this.pending.get(r);if(n)return n;   source: const pending = this.pending.get(cacheKey); if (pending) return pending;
const PATTERN = /(let|const|var)\s+([\w$]+)\s*=\s*this\.pending\.get\(([\w$]+)\);\s*if\s*\(\2\)\s*return\s+\2;/g;
const PATCHED = 'void 0/* elaka360: no shared render promises */';

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const s = lstatSync(p);   // not statSync: pnpm symlinks would visit files twice (or loop)
    if (s.isDirectory()) yield* files(p);
    else if (/\.(m|c)?js$/.test(name)) yield p;
  }
}

let patched = 0;
let already = 0;
for (const file of files(root)) {
  const src = readFileSync(file, 'utf8');
  if (!src.includes('this.pending.get(')) { if (src.includes(PATCHED)) already++; continue; }
  let n = 0;
  const out = src.replace(PATTERN, (_m, kw, name) => { n++; return `${kw} ${name}=${PATCHED};`; });
  if (n === 0) {
    if (/pending\.get\(/.test(src) && /class \w*Batcher|\.batch\(/.test(src)) console.warn(`unrecognised batcher in ${relative(root, file)}`);
    continue;
  }
  writeFileSync(file, out);
  patched += n;
  console.log(`patched ${n} in ${relative(root, file)}`);
}
if (patched === 0 && already === 0) {
  console.error('patch-next-batcher: no Next.js Batcher found in .open-next/server-functions; check the Next.js version');
  process.exit(1);
}
console.log(`patch-next-batcher: ${patched} batcher(s) patched${already ? `, ${already} file(s) already patched` : ''}`);
