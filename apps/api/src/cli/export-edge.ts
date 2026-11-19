/**
 * Snapshot the public API into files for the Cloudflare deployment (Turso/libSQL edge database + static assets).
 *
 * The NestJS API on PostgreSQL stays the reference implementation: this script runs its own services against a
 * database loaded with the seed and writes their exact responses, so the edge Worker (apps/edge-api) only has to
 * look them up. Nothing here is hand-computed that the API computes.
 *
 * Usage (from the repo root, after `pnpm --filter @elaka360/api build` and a migrated + seeded database):
 *   DATABASE_URL=postgres://… node apps/api/dist/cli/export-edge.js
 * Writes:
 *   db/d1/out/<table>.json                  rows for scripts/turso-sync.mjs (each with a content hash `h`), incl. the
 *                                           full-text search tables search_places / search_areas
 *   apps/web/public/data/map/*.json         live-map boundaries, scopes and pin tiles (served as static files)
 */
import 'reflect-metadata';
import { createHash } from 'node:crypto';
import { closeSync, mkdirSync, openSync, rmSync, writeFileSync, writeSync } from 'node:fs';
import { join, resolve } from 'node:path';
import type { AdminAreaSummary, AdminLevel, AreaDetail, AreaStats, Place, PlaceSummary } from '@elaka360/shared';
import { Db } from '../db/db.service';
import { COVERAGE_LEVELS, GeoService, INCLUSION_RULE } from '../geo/geo.service';
import { PlacesService } from '../places/places.service';
import { CategoriesController } from '../categories/categories.controller';
import { EMERGENCY_SQL } from '../emergency/emergency.controller';
import { PLACE_JOINS, PLACE_SUMMARY_COLS } from '../places/places.sql';

const ROOT = resolve(__dirname, '../../../..');
const OUT = join(ROOT, 'db', 'd1', 'out');
const WEB = join(ROOT, 'apps', 'web', 'public', 'data');
const LIST_CHUNK = 2000;                 // ids per area_lists row (keeps each D1 statement well under 100 KB)
// live map: per collected division, its head district and the whole division (apps/web/components/map/LiveMap.tsx);
// order = data/sources/DIVISIONS.md
const DIVISION_HEADS: [number, number][] = [[10002, 20015], [10007, 20059], [10006, 20047], [10001, 20008], [10003, 20027],
  [10004, 20033], [10005, 20036], [10008, 20062]];
const MAP_LEVELS = { coarse: ['upazila', 'city_corporation'], fine: ['union', 'pourashava'] };
const MAX_GEOMETRY_CHARS = 90_000;       // D1 statements are limited to 100 KB
const EV = ['official', 'secondary', 'community', 'unverified'];
// map pins: square tiles of TILE degrees (~5.5 km), loaded by the map for the visible area from zoom 12; the densest
// tile (central Dhaka) stays far below Cloudflare Pages' 25 MiB file limit
const TILE = 0.05;
const tileKey = (lon: number, lat: number) => `${Math.floor(lon / TILE)}_${Math.floor(lat / TILE)}`;
// full-text search rows: the FTS rowid encodes the result order, so `MATCH … LIMIT n` stops after n rows (few rows
// read): places by evidence level then id, areas by level rank then id
const SEARCH_LEVELS = ['division', 'district', 'city_corporation', 'upazila', 'pourashava', 'union', 'ward'];
const placeRid = (ev: string, id: number) => { if (id >= 100_000_000) throw new Error(`place id ${id} too large for the search rowid`); return (EV.indexOf(ev) + 1) * 100_000_000 + id; };
const areaRid = (level: string, id: number) => (SEARCH_LEVELS.indexOf(level) + 1 || 9) * 10_000_000 + id;

const hash = (v: unknown) => createHash('sha1').update(JSON.stringify(v)).digest('hex').slice(0, 16);
const json = (v: unknown) => JSON.stringify(v);
function write(path: string, data: unknown) {
  mkdirSync(join(path, '..'), { recursive: true });
  if (!Array.isArray(data)) return writeFileSync(path, JSON.stringify(data));
  // large tables: one item at a time (a single string for ~500k places exceeds V8's string limit); same bytes as
  // JSON.stringify(array), whose items here are always objects
  const out = arrayWriter(path);
  for (const item of data) out.push(item);
  out.close();
}
/** Streams a JSON array to `path` item by item: the bytes equal JSON.stringify of the whole array. */
function arrayWriter(path: string) {
  mkdirSync(join(path, '..'), { recursive: true });
  const fd = openSync(path, 'w');
  let first = true;
  let buf: string[] = [];
  let size = 0;
  const flush = () => { if (buf.length) { writeSync(fd, buf.join('')); buf = []; size = 0; } };
  writeSync(fd, '[');
  return {
    push(item: unknown) {
      const s = (first ? '' : ',') + JSON.stringify(item);
      first = false;
      buf.push(s); size += s.length;
      if (size > 8_000_000) flush();
    },
    close() { flush(); writeSync(fd, ']'); closeSync(fd); },
  };
}
const EXPORT_CONCURRENCY = Number(process.env.EXPORT_CONCURRENCY ?? 8);   // place-detail queries in flight at once
const summaryOf = (a: AdminAreaSummary): AdminAreaSummary => ({
  id: a.id, level: a.level, parent_id: a.parent_id, name_bn: a.name_bn, name_en: a.name_en, slug: a.slug, path: a.path,
  verified: a.verified, evidence_level: a.evidence_level, production_eligible: a.production_eligible,
});

async function main() {
  // An offline batch job, not a request: the API's 8 s per-query cap is too tight for whole-country queries on a
  // freshly loaded (cold) database. An explicit DB_STATEMENT_TIMEOUT_MS still wins.
  process.env.DB_STATEMENT_TIMEOUT_MS ??= '120000';
  const db = new Db();
  const geo = new GeoService(db);
  const places = new PlacesService(db);
  const t0 = Date.now();
  try {
    // ------------------------------------------------------------------ areas: detail, stats, summary
    const areaRows = await db.many<{ id: number; path: string; parent_id: number | null; level: string }>(
      'SELECT id::int, path, parent_id::int, level::text FROM public_admin_areas ORDER BY id');
    const parent = new Map(areaRows.map((a) => [a.id, a.parent_id]));
    const depthOf = (id: number): number => { let d = 0; let p = parent.get(id); while (p) { d++; p = parent.get(p); } return d; };
    const areas: Record<string, unknown>[] = [];
    const areaSummary = new Map<number, AdminAreaSummary>();
    geo.placeCountMemo = new Map();    // mouzas and villages share their union's counts
    for (let b = 0; b < areaRows.length; b += EXPORT_CONCURRENCY) {
     const batch = areaRows.slice(b, b + EXPORT_CONCURRENCY);
     const details: AreaDetail[] = await Promise.all(batch.map((r) => geo.detailByPath(r.path)));
     for (const detail of details) {
      const a = detail.area;
      const stats: AreaStats = {
        area_id: a.id, descendant_counts: detail.descendant_counts, pending_counts: detail.pending_counts, place_counts: detail.place_counts,
        population_2022: a.population_2022, population_basis: a.population_basis, area_km2: a.area_km2, area_basis: a.area_basis,
        inclusion_rule: INCLUSION_RULE,
      };
      const summary = summaryOf(a);
      areaSummary.set(a.id, summary);
      const row = { id: a.id, path: a.path, parent_id: a.parent_id, level: a.level, depth: depthOf(a.id), name_en: a.name_en,
                    summary: json(summary), detail: json(detail), stats: json(stats) };
      areas.push({ ...row, h: hash(row) });
     }
    }
    geo.placeCountMemo = null;
    console.log(`areas: ${areas.length} (${Date.now() - t0} ms)`);
    const areaKeys = new Map((await db.many<{ id: number; name_key: string | null }>('SELECT id::int, name_key FROM public_admin_areas'))
      .map((r) => [r.id, r.name_key ?? '']));
    const searchAreas = [...areaSummary.values()].filter((a) => a.level !== 'country').map((a) => {
      const row = { rid: areaRid(a.level, a.id), area_id: a.id, level: a.level, name_bn: a.name_bn, name_en: a.name_en ?? '',
                    name_key: areaKeys.get(a.id) ?? '' };
      return { ...row, h: hash(row) };
    });

    // ------------------------------------------------------------------ places: detail by slug, summaries, lists
    const summaries = await db.many<PlaceSummary & { id: number; cat: string; sub: string | null; division_id: number | null;
      district_id: number | null; upazila_id: number | null; union_id: number | null; city_corporation_id: number | null; loc_id: number | null;
      name_key: string | null }>(`
      SELECT p.id::int, ${PLACE_SUMMARY_COLS}, c.key AS cat, sc.key AS sub, p.division_id::int, p.district_id::int,
             p.upazila_id::int, p.union_id::int, p.city_corporation_id::int, loc.id::int AS loc_id, p.name_key
      ${PLACE_JOINS}
      ORDER BY array_position(ARRAY['official','secondary','community','unverified']::text[], p.evidence_level::text),
               p.name_en NULLS LAST, p.name_bn, p.id`);   // = PLACE_LIST_SQL's 'relevance' order, plus id for stable pages
    // place rows are streamed to disk as they are built (only their hashes are kept, for version.json); the
    // detail queries run in small parallel batches, and rows are written in the original order
    const placeOut = arrayWriter(join(OUT, 'places.json'));
    const searchOut = arrayWriter(join(OUT, 'search_places.json'));
    const placeHashes: string[] = [];
    const points: Record<string, unknown>[] = [];
    const lists = new Map<string, number[]>();
    for (let b = 0; b < summaries.length; b += EXPORT_CONCURRENCY) {
     const batch = summaries.slice(b, b + EXPORT_CONCURRENCY);
     const details: Place[] = await Promise.all(batch.map((s) => places.bySlug(s.slug)));
     for (const [i, s] of batch.entries()) {
      const { id, cat, sub, division_id, district_id, upazila_id, union_id, city_corporation_id, loc_id: _loc, name_key, ...summary } = s;
      const detail: Place = details[i];
      const row = { id, slug: summary.slug, summary: json(summary), detail: json(detail) };
      const h = hash(row);
      placeOut.push({ ...row, h });
      placeHashes.push(h);
      // filters for /v1/search: category and sub-category keys, and the ids of every area the place lies in
      const srow = { rid: placeRid(summary.evidence_level, id), place_id: id, name_bn: summary.name_bn, name_en: summary.name_en ?? '',
                     name_key: name_key ?? '', cat: [cat, sub ?? ''].join(' ').trim(),
                     areas: ` ${[division_id, district_id, upazila_id, union_id, city_corporation_id].filter((x) => x !== null).join(' ')} ` };
      searchOut.push({ ...srow, h: hash(srow) });
      if (summary.lat !== null && summary.lon !== null) {
        const pt = { id, lat: summary.lat, lon: summary.lon, division_id, district_id, upazila_id, union_id, city_corporation_id,
                     category_key: cat, subcategory_key: sub, summary: json(summary) };
        points.push({ ...pt, h: hash(pt) });
      }
      // area 0 = no area filter (national list); categories: all, top level, sub level
      const areaKeys = new Set([0, division_id, district_id, upazila_id, union_id, city_corporation_id].filter((x): x is number => x !== null));
      for (const aid of areaKeys) for (const c of new Set(['', cat, sub ?? ''])) {
        const k = `${aid}|${c}`;
        (lists.get(k) ?? lists.set(k, []).get(k)!).push(id);
      }
     }
    }
    placeOut.close();
    searchOut.close();
    const listRows: Record<string, unknown>[] = [];
    for (const [k, ids] of lists) {
      const [aid, cat] = k.split('|');
      for (let i = 0; i * LIST_CHUNK < ids.length; i++) {
        const row = { area_id: Number(aid), cat, chunk: i, total: ids.length, ids: json(ids.slice(i * LIST_CHUNK, (i + 1) * LIST_CHUNK)) };
        listRows.push({ ...row, h: hash(row) });
      }
    }
    console.log(`places: ${placeHashes.length}, points: ${points.length}, list rows: ${listRows.length} (${Date.now() - t0} ms)`);

    // ------------------------------------------------------------------ boundaries (locate, boundary endpoints)
    const bRows: Record<string, unknown>[] = [];
    const raw = await db.many<{ id: number; level: string; path: string; minx: number; miny: number; maxx: number; maxy: number }>(`
      SELECT id::int, level::text, path, ST_XMin(boundary::geometry) AS minx, ST_YMin(boundary::geometry) AS miny,
             ST_XMax(boundary::geometry) AS maxx, ST_YMax(boundary::geometry) AS maxy
      FROM public_admin_areas WHERE boundary IS NOT NULL ORDER BY id`);
    for (const b of raw) {
      let geometry = '';
      for (const tol of [0, 0.0001, 0.0003, 0.001, 0.003]) {   // full detail when it fits, simplified otherwise
        const g = await db.one<{ g: string }>(
          `SELECT ST_AsGeoJSON(${tol ? `ST_SimplifyPreserveTopology(boundary::geometry, ${tol})` : 'boundary::geometry'}, 5) AS g
           FROM public_admin_areas WHERE id = $1`, [b.id]);
        geometry = g!.g;
        if (geometry.length <= MAX_GEOMETRY_CHARS) break;
      }
      if (geometry.length > MAX_GEOMETRY_CHARS) throw new Error(`boundary ${b.id} still too large`);
      const row = { ...b, summary: json(areaSummary.get(b.id)), geometry };
      bRows.push({ ...row, h: hash(row) });
    }
    console.log(`boundaries: ${bRows.length} (${Date.now() - t0} ms)`);

    // ------------------------------------------------------------------ small documents (meta table)
    const levels = (await db.many<{ level: string }>('SELECT DISTINCT level::text FROM public_admin_areas WHERE boundary IS NOT NULL ORDER BY 1')).map((r) => r.level);
    // coverage reports: country, divisions, districts and upazilas (the edge serves them by id)
    const coverage: Record<string, unknown> = {};
    for (const r of areaRows.filter((a) => COVERAGE_LEVELS.includes(a.level as AdminLevel))) coverage[`coverage:${r.id}`] = await geo.coverage(r.id);
    console.log(`coverage reports: ${Object.keys(coverage).length} (${Date.now() - t0} ms)`);
    const docs: Record<string, unknown> = {
      ...coverage,
      'stats:national': await geo.nationalStats(),
      'categories': await new CategoriesController(db).tree(),
      'emergency': await db.many(EMERGENCY_SQL),
      'boundary_levels': levels,
      'inclusion_rule': INCLUSION_RULE,
    };
    const meta = Object.entries(docs).map(([key, v]) => { const row = { key, value: json(v) }; return { ...row, h: hash(row) }; });

    for (const [name, rows] of Object.entries({ areas, place_points: points, area_lists: listRows, boundaries: bRows, meta,
                                                search_areas: searchAreas })) {
      write(join(OUT, `${name}.json`), rows);
    }

    // ------------------------------------------------------------------ static files for the website
    // a division is on the map once it has places with a location; per division: boundaries + pins, listed in scopes.json
    const pinFields = ['slug', 'name_bn', 'name_en', 'category_key', 'subcategory_key', 'area_label_bn', 'area_label_en',
                       'evidence_level', 'production_eligible', 'lat', 'lon', 'district_id'] as const;
    const scopes: { id: number; kind: 'district' | 'division'; division_id: number; name_bn: string; name_en: string }[] = [];
    rmSync(join(WEB, 'map'), { recursive: true, force: true });     // drop tiles and files of an earlier layout
    for (const [divId, headId] of DIVISION_HEADS) {
      if (!summaries.some((s) => s.lat !== null && s.division_id === divId)) continue;
      for (const [id, kind] of [[headId, 'district'], [divId, 'division']] as const) {
        for (const [group, lv] of Object.entries(MAP_LEVELS)) write(join(WEB, 'map', `b-${id}-${group}.json`), await geo.childBoundaries(id, lv));
        const a = areaSummary.get(id)!;
        scopes.push({ id, kind, division_id: divId, name_bn: a.name_bn, name_en: a.name_en });
      }
    }
    write(join(WEB, 'map', 'scopes.json'), scopes);
    // pins: one file per tile, in list order; tiles.json lists the tiles that exist (the map never asks for empty ones)
    const tiles = new Map<string, unknown[][]>();
    for (const s of summaries) {
      if (s.lat === null || s.lon === null) continue;
      const k = tileKey(s.lon, s.lat);
      (tiles.get(k) ?? tiles.set(k, []).get(k)!).push(pinFields.map((f) => (s as unknown as Record<string, unknown>)[f] ?? null));
    }
    for (const [k, rows] of tiles) write(join(WEB, 'map', 'tiles', `${k}.json`), { fields: pinFields, rows });
    write(join(WEB, 'map', 'tiles.json'), { size: TILE, min_zoom: 12, tiles: Object.fromEntries([...tiles].map(([k, r]) => [k, r.length])) });

    // search runs in the edge database (search_places / search_areas); no static index any more
    rmSync(join(WEB, 'search'), { recursive: true, force: true });
    write(join(WEB, 'map', 'version.json'), { data: hash([areas.map((a) => a.h), placeHashes]) });
    console.log(`export-edge: done in ${Date.now() - t0} ms → ${OUT}, ${WEB}/{map,search}`);
  } finally {
    await db.onModuleDestroy();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
