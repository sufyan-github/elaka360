/**
 * Snapshot the public API into files for the Cloudflare deployment (D1 + static assets).
 *
 * The NestJS API on PostgreSQL stays the reference implementation: this script runs its own services against a
 * database loaded with the seed and writes their exact responses, so the edge Worker (apps/edge-api) only has to
 * look them up. Nothing here is hand-computed that the API computes.
 *
 * Usage (from the repo root, after `pnpm --filter @elaka360/api build` and a migrated + seeded database):
 *   DATABASE_URL=postgres://… node apps/api/dist/cli/export-edge.js
 * Writes:
 *   db/d1/out/<table>.json                  rows for scripts/d1-sync.mjs (each with a content hash `h`)
 *   apps/web/public/data/map/*.json         live-map boundaries and pins (served as static files)
 *   apps/web/public/data/search/*.json      the in-browser search index
 */
import 'reflect-metadata';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import type { AdminAreaSummary, AreaDetail, AreaStats, Place, PlaceSummary } from '@elaka360/shared';
import { Db } from '../db/db.service';
import { GeoService, INCLUSION_RULE } from '../geo/geo.service';
import { PlacesService } from '../places/places.service';
import { CategoriesController } from '../categories/categories.controller';
import { EMERGENCY_SQL } from '../emergency/emergency.controller';
import { PLACE_JOINS, PLACE_SUMMARY_COLS } from '../places/places.sql';

const ROOT = resolve(__dirname, '../../../..');
const OUT = join(ROOT, 'db', 'd1', 'out');
const WEB = join(ROOT, 'apps', 'web', 'public', 'data');
const LIST_CHUNK = 2000;                 // ids per area_lists row (keeps each D1 statement well under 100 KB)
const MAP_SCOPES = [20015, 10002];       // Rajshahi District, Rajshahi Division (apps/web/components/map/LiveMap.tsx)
const MAP_LEVELS = { coarse: ['upazila', 'city_corporation'], fine: ['union', 'pourashava'] };
const MAX_GEOMETRY_CHARS = 90_000;       // D1 statements are limited to 100 KB
const EV = ['official', 'secondary', 'community', 'unverified'];

const hash = (v: unknown) => createHash('sha1').update(JSON.stringify(v)).digest('hex').slice(0, 16);
const json = (v: unknown) => JSON.stringify(v);
function write(path: string, data: unknown) {
  mkdirSync(join(path, '..'), { recursive: true });
  writeFileSync(path, JSON.stringify(data));
}
const summaryOf = (a: AdminAreaSummary): AdminAreaSummary => ({
  id: a.id, level: a.level, parent_id: a.parent_id, name_bn: a.name_bn, name_en: a.name_en, slug: a.slug, path: a.path,
  verified: a.verified, evidence_level: a.evidence_level, production_eligible: a.production_eligible,
});

async function main() {
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
    for (const r of areaRows) {
      const detail: AreaDetail = await geo.detailByPath(r.path);
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
    console.log(`areas: ${areas.length} (${Date.now() - t0} ms)`);

    // ------------------------------------------------------------------ places: detail by slug, summaries, lists
    const summaries = await db.many<PlaceSummary & { id: number; cat: string; sub: string | null; division_id: number | null;
      district_id: number | null; upazila_id: number | null; union_id: number | null; city_corporation_id: number | null; loc_id: number | null }>(`
      SELECT p.id::int, ${PLACE_SUMMARY_COLS}, c.key AS cat, sc.key AS sub, p.division_id::int, p.district_id::int,
             p.upazila_id::int, p.union_id::int, p.city_corporation_id::int, loc.id::int AS loc_id
      ${PLACE_JOINS}
      ORDER BY array_position(ARRAY['official','secondary','community','unverified']::text[], p.evidence_level::text),
               p.name_en NULLS LAST, p.name_bn, p.id`);   // = PLACE_LIST_SQL's 'relevance' order, plus id for stable pages
    const placeRows: Record<string, unknown>[] = [];
    const points: Record<string, unknown>[] = [];
    const lists = new Map<string, number[]>();
    for (const s of summaries) {
      const { id, cat, sub, division_id, district_id, upazila_id, union_id, city_corporation_id, loc_id: _loc, ...summary } = s;
      const detail: Place = await places.bySlug(summary.slug);
      const row = { id, slug: summary.slug, summary: json(summary), detail: json(detail) };
      placeRows.push({ ...row, h: hash(row) });
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
    const listRows: Record<string, unknown>[] = [];
    for (const [k, ids] of lists) {
      const [aid, cat] = k.split('|');
      for (let i = 0; i * LIST_CHUNK < ids.length; i++) {
        const row = { area_id: Number(aid), cat, chunk: i, total: ids.length, ids: json(ids.slice(i * LIST_CHUNK, (i + 1) * LIST_CHUNK)) };
        listRows.push({ ...row, h: hash(row) });
      }
    }
    console.log(`places: ${placeRows.length}, points: ${points.length}, list rows: ${listRows.length} (${Date.now() - t0} ms)`);

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
    const docs: Record<string, unknown> = {
      'stats:national': await geo.nationalStats(),
      'categories': await new CategoriesController(db).tree(),
      'emergency': await db.many(EMERGENCY_SQL),
      'boundary_levels': levels,
      'inclusion_rule': INCLUSION_RULE,
    };
    const meta = Object.entries(docs).map(([key, v]) => { const row = { key, value: json(v) }; return { ...row, h: hash(row) }; });

    for (const [name, rows] of Object.entries({ areas, places: placeRows, place_points: points, area_lists: listRows, boundaries: bRows, meta })) {
      write(join(OUT, `${name}.json`), rows);
    }

    // ------------------------------------------------------------------ static files for the website
    for (const id of MAP_SCOPES) {
      for (const [group, lv] of Object.entries(MAP_LEVELS)) write(join(WEB, 'map', `b-${id}-${group}.json`), await geo.childBoundaries(id, lv));
    }
    // pins: everything with a location inside Rajshahi Division (the map's widest scope)
    const pinFields = ['slug', 'name_bn', 'name_en', 'category_key', 'subcategory_key', 'area_label_bn', 'area_label_en',
                       'evidence_level', 'production_eligible', 'lat', 'lon', 'district_id'] as const;
    const pins = summaries.filter((s) => s.lat !== null && s.division_id === 10002)
      .map((s) => pinFields.map((f) => (s as unknown as Record<string, unknown>)[f] ?? null));
    write(join(WEB, 'map', 'pins-10002.json'), { fields: pinFields, rows: pins });

    // search index: areas (excluding the country) and places, as field lists + rows
    const aFields = ['id', 'level', 'parent_id', 'name_bn', 'name_en', 'slug', 'path', 'verified', 'evidence_level', 'production_eligible'] as const;
    write(join(WEB, 'search', 'areas.json'), {
      fields: aFields,
      rows: [...areaSummary.values()].filter((a) => a.level !== 'country').map((a) => aFields.map((f) => a[f])),
    });
    // places: compact rows; the area label is rebuilt in the browser from the areas index (loc_id, district_id),
    // categories are indexes into `cats`, evidence an index into EV
    const cats = [...new Set(summaries.map((s) => s.subcategory_key ?? s.category_key))].sort();
    const catIdx = new Map(cats.map((c, i) => [c, i]));
    write(join(WEB, 'search', 'places.json'), {
      fields: ['slug', 'name_bn', 'name_en', 'cat', 'loc_id', 'district_id', 'ev'],
      cats, ev: EV,
      rows: summaries.map((s) => [s.slug, s.name_bn, s.name_en, catIdx.get(s.subcategory_key ?? s.category_key),
                                  s.loc_id, s.district_id, EV.indexOf(s.evidence_level)]),
    });
    write(join(WEB, 'search', 'version.json'), { data: hash([areas.map((a) => a.h), placeRows.map((p) => p.h)]) });
    console.log(`export-edge: done in ${Date.now() - t0} ms → ${OUT}, ${WEB}/{map,search}`);
  } finally {
    await db.onModuleDestroy();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
