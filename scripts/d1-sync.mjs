#!/usr/bin/env node
// Bring the D1 database in line with db/d1/out/*.json (written by apps/api/dist/cli/export-edge.js).
// Only rows whose content hash changed are written, so normal releases cost few of the free plan's
// 100,000 rows written per day. The first load is the big one (~80k); if a run would pass --budget it stops
// early, and running it again (e.g. the next day) continues where it left off.
//
// Usage: node scripts/d1-sync.mjs (--local | --remote) [--budget 95000] [--dry-run]
// Needs CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID for --remote. Uses apps/edge-api/wrangler.jsonc (binding DB).
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const API = join(ROOT, 'apps', 'edge-api');
const OUT = join(ROOT, 'db', 'd1', 'out');
const args = process.argv.slice(2);
const mode = args.includes('--remote') ? '--remote' : args.includes('--local') ? '--local' : null;
if (!mode) { console.error('usage: d1-sync.mjs (--local | --remote) [--budget N] [--dry-run]'); process.exit(2); }
const budget = Number(args[args.indexOf('--budget') + 1]) || 95_000;
const dryRun = args.includes('--dry-run');

// table → key columns, all columns, rows written per insert/delete (1 + number of indexes)
const TABLES = [
  { name: 'meta', key: ['key'], cols: ['key', 'value', 'h'], cost: 1 },
  { name: 'areas', key: ['id'], cols: ['id', 'path', 'parent_id', 'level', 'depth', 'name_en', 'summary', 'detail', 'stats', 'h'], cost: 3 },
  { name: 'boundaries', key: ['id'], cols: ['id', 'level', 'path', 'minx', 'miny', 'maxx', 'maxy', 'summary', 'geometry', 'h'], cost: 2 },
  { name: 'area_lists', key: ['area_id', 'cat', 'chunk'], cols: ['area_id', 'cat', 'chunk', 'total', 'ids', 'h'], cost: 1 },
  { name: 'place_points', key: ['id'], cols: ['id', 'lat', 'lon', 'division_id', 'district_id', 'upazila_id', 'union_id', 'city_corporation_id', 'category_key', 'subcategory_key', 'summary', 'h'], cost: 2 },
  { name: 'places', key: ['id'], cols: ['id', 'slug', 'summary', 'detail', 'h'], cost: 2 },
];

function wrangler(extra) {
  return execFileSync('npx', ['wrangler', 'd1', 'execute', 'DB', mode, ...extra], {
    cwd: API, encoding: 'utf8', maxBuffer: 1 << 30, stdio: ['ignore', 'pipe', 'inherit'],
  });
}
const lit = (v) => (v === null || v === undefined ? 'NULL' : typeof v === 'number' ? String(v) : typeof v === 'boolean' ? (v ? '1' : '0')
  : `'${String(v).replace(/'/g, "''")}'`);
const keyOf = (t, r) => t.key.map((k) => r[k]).join('|');

console.log(`d1-sync: schema (${mode})`);
if (!dryRun) wrangler(['--file', join(ROOT, 'db', 'd1', 'schema.sql'), '--yes']);

const statements = [];
let writes = 0;
let stoppedEarly = false;
for (const t of TABLES) {
  const want = JSON.parse(readFileSync(join(OUT, `${t.name}.json`), 'utf8'));
  const have = new Map();
  if (!dryRun || mode === '--local') {
    const res = JSON.parse(wrangler(['--json', '--command', `SELECT ${t.key.join(', ')}, h FROM ${t.name}`]));
    for (const r of res[0]?.results ?? []) have.set(keyOf(t, r), r.h);
  }
  const wantKeys = new Set(want.map((r) => keyOf(t, r)));
  const gone = [...have.keys()].filter((k) => !wantKeys.has(k));
  const changed = want.filter((r) => have.get(keyOf(t, r)) !== r.h);
  // a partial load should cover what visitors reach first: the curated pilot places (lowest ids), then places shown
  // on the map, then the rest
  if (t.name === 'places') {
    const pinned = new Set(JSON.parse(readFileSync(join(OUT, 'place_points.json'), 'utf8')).map((p) => p.id));
    const rank = (r) => (r.id <= 100 ? 0 : pinned.has(r.id) ? 1 : 2);
    changed.sort((x, y) => rank(x) - rank(y) || x.id - y.id);
  }
  let applied = 0;
  for (const k of gone) {
    if (writes + t.cost > budget) { stoppedEarly = true; break; }
    const parts = k.split('|');
    statements.push(`DELETE FROM ${t.name} WHERE ${t.key.map((c, i) => `${c} = ${lit(isNaN(Number(parts[i])) || c === 'cat' ? parts[i] : Number(parts[i]))}`).join(' AND ')};`);
    writes += t.cost;
  }
  for (const r of changed) {
    const cost = have.has(keyOf(t, r)) ? 2 * t.cost : t.cost;   // REPLACE = delete + insert
    if (writes + cost > budget) { stoppedEarly = true; break; }
    statements.push(`INSERT OR REPLACE INTO ${t.name} (${t.cols.join(', ')}) VALUES (${t.cols.map((c) => lit(r[c])).join(', ')});`);
    writes += cost;
    applied++;
  }
  console.log(`d1-sync: ${t.name}: ${want.length} rows, ${changed.length} new/changed, ${gone.length} removed${applied < changed.length ? ` (applying ${applied} now)` : ''}`);
  if (stoppedEarly) break;
}

console.log(`d1-sync: ${statements.length} statements, ~${writes} rows written (budget ${budget})`);
if (statements.length && !dryRun) {
  const file = join(mkdtempSync(join(tmpdir(), 'd1-sync-')), 'changes.sql');
  writeFileSync(file, statements.join('\n') + '\n');
  wrangler(['--file', file, '--yes']);
}
if (stoppedEarly) {
  console.log('d1-sync: stopped at the write budget; run it again after 00:00 UTC to finish (the site keeps serving the rows already loaded)');
  process.exit(10);
}
console.log('d1-sync: up to date');
