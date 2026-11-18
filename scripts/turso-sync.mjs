#!/usr/bin/env node
// Bring the edge database (Turso / libSQL) in line with db/d1/out/*.json (written by apps/api/dist/cli/export-edge.js).
// Only rows whose content hash `h` changed are written and rows that disappeared are deleted, so a normal release
// costs few of the free plan's 10 million rows written per month. The first load is the big one (~1.6 million rows);
// --budget stops a run before a limit and the next run continues where it left off.
//
// Usage: node scripts/turso-sync.mjs [--url URL] [--token TOKEN] [--budget N] [--dry-run] [--only table,table]
//   URL / TOKEN default to TURSO_DATABASE_URL / TURSO_AUTH_TOKEN; without them, a local libSQL server
//   (http://127.0.0.1:8080, e.g. `docker run -p 8080:8080 ghcr.io/tursodatabase/libsql-server`).
import { createReadStream, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createClient } from '@libsql/client';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'db', 'd1', 'out');
const SCHEMA = join(ROOT, 'db', 'd1', 'schema.sql');
const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const url = opt('--url') ?? process.env.TURSO_DATABASE_URL ?? 'http://127.0.0.1:8080';
const authToken = opt('--token') ?? process.env.TURSO_AUTH_TOKEN;
const budget = Number(opt('--budget')) || Infinity;
const dryRun = args.includes('--dry-run');
const only = opt('--only')?.split(',');

// table → key columns, the export field that holds the key (FTS tables: rowid ← rid), all value columns, FTS or not
const TABLES = [
  { name: 'meta', key: ['key'], cols: ['key', 'value', 'h'] },
  { name: 'areas', key: ['id'], cols: ['id', 'path', 'parent_id', 'level', 'depth', 'name_en', 'summary', 'detail', 'stats', 'h'] },
  { name: 'boundaries', key: ['id'], cols: ['id', 'level', 'path', 'minx', 'miny', 'maxx', 'maxy', 'summary', 'geometry', 'h'] },
  { name: 'area_lists', key: ['area_id', 'cat', 'chunk'], cols: ['area_id', 'cat', 'chunk', 'total', 'ids', 'h'] },
  { name: 'place_points', key: ['id'], cols: ['id', 'lat', 'lon', 'division_id', 'district_id', 'upazila_id', 'union_id', 'city_corporation_id', 'category_key', 'subcategory_key', 'summary', 'h'] },
  { name: 'places', key: ['id'], cols: ['id', 'slug', 'summary', 'detail', 'h'] },
  { name: 'search_areas', fts: true, key: ['rowid'], from: { rowid: 'rid' }, cols: ['name_bn', 'name_en', 'name_key', 'area_id', 'level', 'h'] },
  { name: 'search_places', fts: true, key: ['rowid'], from: { rowid: 'rid' }, cols: ['name_bn', 'name_en', 'name_key', 'place_id', 'cat', 'areas', 'h'] },
];
const BATCH_ROWS = 200;
const BATCH_CHARS = 3_000_000;

/** Items of a JSON array file, one at a time (the export's places.json is larger than a JS string may be). */
async function* jsonArrayItems(path) {
  let depth = 0, inStr = false, esc = false, buf = '', start = -1;
  for await (const chunk of createReadStream(path, { encoding: 'utf8', highWaterMark: 1 << 20 })) {
    let from = 0;
    for (let i = 0; i < chunk.length; i++) {
      const c = chunk[i];
      if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; continue; }
      if (c === '"') { inStr = true; continue; }
      if (c === '{' || c === '[') {
        depth++;
        if (depth === 2 && start < 0) { start = i; from = i; buf = ''; }
      } else if (c === '}' || c === ']') {
        depth--;
        if (depth === 1 && start >= 0) {
          yield JSON.parse(buf + chunk.slice(from, i + 1));
          start = -1; buf = '';
        }
      }
    }
    if (start >= 0) { buf += chunk.slice(from); start = 0; }
  }
}

const keyOf = (t, row) => t.key.map((k) => row[t.from?.[k] ?? k]).join('\u0001');

async function existing(db, t) {
  // keyset pages (row-value comparison for composite keys): the server limits the size of one response
  const have = new Map();
  const cols = t.key.join(', ');
  const PAGE = 5000;
  let last = null;
  for (;;) {
    const where = last ? `WHERE (${cols}) > (${t.key.map(() => '?').join(', ')})` : '';
    const r = await db.execute({ sql: `SELECT ${cols}, h FROM ${t.name} ${where} ORDER BY ${cols} LIMIT ${PAGE}`, args: last ?? [] });
    for (const row of r.rows) have.set(t.key.map((k) => row[k]).join('\u0001'), row.h);
    if (r.rows.length < PAGE) break;
    const end = r.rows.at(-1);
    last = t.key.map((k) => end[k]);
  }
  return have;
}

function upsert(t, row, existed) {
  if (!t.fts) {
    return [{ sql: `INSERT OR REPLACE INTO ${t.name}(${t.cols.join(',')}) VALUES (${t.cols.map(() => '?').join(',')})`,
              args: t.cols.map((c) => row[c] ?? null) }];
  }
  const rowid = row[t.from.rowid];
  return [
    ...(existed ? [{ sql: `DELETE FROM ${t.name} WHERE rowid = ?`, args: [rowid] }] : []),
    { sql: `INSERT INTO ${t.name}(rowid, ${t.cols.join(',')}) VALUES (?, ${t.cols.map(() => '?').join(',')})`,
      args: [rowid, ...t.cols.map((c) => row[c] ?? null)] },
  ];
}

function deleteStmt(t, key) {
  const parts = key.split('\u0001');
  return { sql: `DELETE FROM ${t.name} WHERE ${t.key.map((k) => `${k} = ?`).join(' AND ')}`,
           args: parts.map((p, i) => (t.key[i] === 'cat' || t.key[i] === 'key' ? p : Number(p))) };
}

async function main() {
  const db = createClient({ url, authToken });
  const host = new URL(url.replace(/^libsql:/, 'https:')).host;
  console.log(`turso-sync → ${host}${dryRun ? ' (dry run)' : ''}`);
  const schema = readFileSync(SCHEMA, 'utf8').split('\n').filter((l) => !l.trim().startsWith('--')).join('\n')
    .split(';').map((s) => s.trim()).filter(Boolean);
  if (!dryRun) {
    // full-text tables hold derived rows only: when their columns differ from the schema, drop them so the schema
    // recreates them and this run reloads them (CREATE … IF NOT EXISTS would keep the old layout)
    for (const t of TABLES.filter((x) => x.fts)) {
      const info = await db.execute(`PRAGMA table_info(${t.name})`);
      const have = info.rows.map((r) => r.name).join(',');
      if (have && have !== ['name_bn', 'name_en', 'name_key', ...t.cols.slice(3)].join(',')) {
        console.log(`${t.name}: columns changed (${have}); rebuilding`);
        await db.execute(`DROP TABLE ${t.name}`);
      }
    }
    await db.batch(schema, 'write');
  }

  let written = 0;
  for (const t of TABLES) {
    if (only && !only.includes(t.name)) continue;
    const have = await existing(db, t);
    const changed = []; let chars = 0; let ins = 0, upd = 0;
    const flush = async () => {
      if (!changed.length) return;
      if (!dryRun) await db.batch(changed.splice(0), 'write'); else changed.length = 0;
      chars = 0;
    };
    let stopped = false;
    for await (const row of jsonArrayItems(join(OUT, `${t.name}.json`))) {
      const k = keyOf(t, row);
      const prev = have.get(k);
      have.delete(k);
      if (prev === row.h) continue;
      if (written >= budget) { stopped = true; break; }
      const stmts = upsert(t, row, prev !== undefined);
      changed.push(...stmts);
      chars += JSON.stringify(stmts[stmts.length - 1].args).length;
      written++;
      if (prev === undefined) ins++; else upd++;
      if (changed.length >= BATCH_ROWS || chars >= BATCH_CHARS) await flush();
    }
    let del = 0;
    if (!stopped) {
      for (const k of have.keys()) {
        if (written >= budget) { stopped = true; break; }
        changed.push(deleteStmt(t, k)); written++; del++;
        if (changed.length >= BATCH_ROWS) await flush();
      }
    }
    await flush();
    console.log(`${t.name}: +${ins} ~${upd} -${del}${stopped ? ' (budget reached: run again to continue)' : ''}`);
    if (stopped) break;
  }
  console.log(`rows written: ${written}${Number.isFinite(budget) ? ` of budget ${budget}` : ''}`);
  db.close();
}

main().catch((e) => { console.error(e); process.exit(1); });
