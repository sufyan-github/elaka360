/**
 * Elaka360 public read API on Cloudflare Workers + D1.
 *
 * Responses are snapshots of the NestJS API (apps/api), written to D1 by apps/api/src/cli/export-edge.ts and
 * scripts/d1-sync.mjs, so this Worker mostly looks rows up: little CPU per request (free plan: 10 ms) and few
 * D1 rows read (free plan: 5 million a day). Search runs in the browser (apps/web/lib/browser-search.ts).
 * Sign-in, contributions and the admin API are not served here yet: they answer 503.
 */
import { covers, distanceM, type Geometry } from './geo';

export interface Env {
  DB: D1Database;
  APP_VERSION?: string;
  EDGE_SHARED_SECRET?: string;
}

// Minimal D1 types (avoids a dependency on @cloudflare/workers-types)
interface D1Result<T> { results: T[] }
interface D1PreparedStatement {
  bind(...values: unknown[]): D1PreparedStatement;
  first<T = Record<string, unknown>>(): Promise<T | null>;
  all<T = Record<string, unknown>>(): Promise<D1Result<T>>;
  run(): Promise<unknown>;
}
export interface D1Database { prepare(sql: string): D1PreparedStatement }

const LEVEL_ORDER = ['country', 'division', 'district', 'upazila', 'city_corporation', 'pourashava', 'union', 'ward', 'mouza', 'village', 'thana'];
const LEVELS = new Set(['division', 'district', 'upazila', 'city_corporation', 'pourashava', 'union', 'ward']);
const LOCATE_ORDER = ['union', 'pourashava', 'city_corporation', 'upazila', 'district', 'division'];
const SLUG_RE = /^[a-z0-9-]{1,120}$/;
const CATEGORY_RE = /^[a-z_]{2,40}(\.[a-z_]{2,40})?$/;
const IP_RE = /^[0-9a-fA-F:.]{2,45}$/;
const LIST_CHUNK = 2000;

class HttpError extends Error {
  constructor(public status: number, public title: string, detail: string) { super(detail); }
}
const bad = (detail: string) => new HttpError(400, 'Bad Request', detail);
const notFound = (detail: string) => new HttpError(404, 'Not Found', detail);

/* ---------------------------------------------------------------- params (same rules as apps/api/src/common/params.ts) */

function intParam(v: string | null, name: string, o: { min?: number; max?: number; def?: number } = {}): number | undefined {
  if (v === null || v === '') return o.def;
  if (!/^-?\d{1,16}$/.test(v)) throw bad(`${name} must be an integer`);
  const n = Number(v);
  if (!Number.isSafeInteger(n)) throw bad(`${name} must be an integer`);
  if (o.min !== undefined && n < o.min) throw bad(`${name} must be >= ${o.min}`);
  if (o.max !== undefined && n > o.max) throw bad(`${name} must be <= ${o.max}`);
  return n;
}
function idParam(v: string | undefined, name = 'id'): number {
  const n = intParam(v ?? null, name, { min: 1 });
  if (n === undefined) throw bad(`${name} is required`);
  return n;
}
function floatParam(v: string | null, name: string, min: number, max: number): number {
  const n = Number(v);
  if (v === null || v === '' || !Number.isFinite(n) || n < min || n > max) throw bad(`${name} must be a number between ${min} and ${max}`);
  return n;
}
const cursor = {
  encode: (offset: number) => btoa(String(offset)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''),
  decode: (v: string | null): number => {
    if (!v) return 0;
    let n = NaN;
    try { n = Number(atob(v.replace(/-/g, '+').replace(/_/g, '/'))); } catch { /* invalid */ }
    if (!Number.isInteger(n) || n < 0 || n > 1_000_000) throw bad('invalid cursor');
    return n;
  },
};
function normalisePath(raw: string | null): string {
  const p = (raw ?? '').trim().replace(/^\/+|\/+$/g, '').toLowerCase();
  if (!p) return 'bangladesh';
  if (p.length > 200 || !/^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(p)) throw bad('invalid path');
  return p;
}
function category(raw: string | null): string | undefined {
  if (!raw) return undefined;
  if (!CATEGORY_RE.test(raw)) throw bad('invalid category');
  return raw;
}

/* ---------------------------------------------------------------- data access */

const parse = <T>(s: string | null | undefined): T => JSON.parse(s ?? 'null') as T;

async function meta<T>(db: D1Database, key: string): Promise<T> {
  const row = await db.prepare('SELECT value FROM meta WHERE key = ?').bind(key).first<{ value: string }>();
  if (!row) throw new HttpError(503, 'Service Unavailable', 'data not loaded yet');
  return parse<T>(row.value);
}
async function areaRow(db: D1Database, where: 'id' | 'path', v: number | string, col: 'detail' | 'stats' | 'summary') {
  const row = await db.prepare(`SELECT ${col} AS v FROM areas WHERE ${where} = ?`).bind(v).first<{ v: string }>();
  if (!row) throw notFound(`area not found: ${v}`);
  return parse<Record<string, unknown>>(row.v);
}

async function placeList(db: D1Database, areaId: number | undefined, cat: string | undefined, limit: number, offset: number) {
  const area = areaId ?? 0;
  const c = cat ?? '';
  const first = Math.floor(offset / LIST_CHUNK);
  const last = Math.floor((offset + limit - 1) / LIST_CHUNK);
  const { results } = await db.prepare('SELECT chunk, total, ids FROM area_lists WHERE area_id = ? AND cat = ? AND chunk BETWEEN ? AND ? ORDER BY chunk')
    .bind(area, c, first, last).all<{ chunk: number; total: number; ids: string }>();
  let total = results[0]?.total;
  if (total === undefined) {
    const t = await db.prepare('SELECT total FROM area_lists WHERE area_id = ? AND cat = ? LIMIT 1').bind(area, c).first<{ total: number }>();
    total = t?.total ?? 0;
  }
  const ids = results.flatMap((r) => parse<number[]>(r.ids)).slice(offset - first * LIST_CHUNK, offset - first * LIST_CHUNK + limit);
  if (!ids.length) return { items: [], total };
  const rows = await db.prepare(`SELECT id, summary FROM places WHERE id IN (${ids.map(() => '?').join(',')})`).bind(...ids).all<{ id: number; summary: string }>();
  const byId = new Map(rows.results.map((r) => [r.id, parse<Record<string, unknown>>(r.summary)]));
  return { items: ids.map((id) => byId.get(id)).filter(Boolean), total };
}

async function tree(db: D1Database, rootId: number, depth: number) {
  const root = await db.prepare('SELECT path, depth FROM areas WHERE id = ?').bind(rootId).first<{ path: string; depth: number }>();
  if (!root) throw notFound(`area not found: ${rootId}`);
  // the country's children (divisions) do not share its path prefix, so the root is matched by depth only
  const sql = rootId === 1
    ? 'SELECT summary, depth FROM areas WHERE depth <= ?'
    : "SELECT summary, depth FROM areas WHERE depth <= ? AND (path = ? OR path LIKE ? || '/%')";
  const stmt = rootId === 1 ? db.prepare(sql).bind(root.depth + depth) : db.prepare(sql).bind(root.depth + depth, root.path, root.path);
  const { results } = await stmt.all<{ summary: string; depth: number }>();
  type Node = Record<string, unknown> & { id: number; parent_id: number | null; level: string; name_en: string; children?: Node[] };
  const nodes = results.map((r) => ({ node: parse<Node>(r.summary), depth: r.depth }));
  nodes.sort((a, b) => a.depth - b.depth || LEVEL_ORDER.indexOf(a.node.level) - LEVEL_ORDER.indexOf(b.node.level)
    || (a.node.name_en ?? '').localeCompare(b.node.name_en ?? ''));
  const byId = new Map(nodes.map((n) => [n.node.id, n.node]));
  for (const { node } of nodes) {
    if (node.id === rootId || node.parent_id === null) continue;
    const parent = byId.get(node.parent_id);
    if (parent) (parent.children ??= []).push(node);
  }
  return byId.get(rootId);
}

async function locate(db: D1Database, lat: number, lon: number) {
  const { results } = await db.prepare(
    'SELECT id, level, summary, geometry FROM boundaries WHERE minx <= ? AND maxx >= ? AND miny <= ? AND maxy >= ?')
    .bind(lon, lon, lat, lat).all<{ id: number; level: string; summary: string; geometry: string }>();
  results.sort((a, b) => LOCATE_ORDER.indexOf(a.level) - LOCATE_ORDER.indexOf(b.level));
  const hit = results.find((r) => LOCATE_ORDER.includes(r.level) && covers(parse<Geometry>(r.geometry), lon, lat));
  const levels = await meta<string[]>(db, 'boundary_levels');
  if (!hit) return { lat, lon, area: null, breadcrumb: [], resolved_levels: levels };
  const detail = await areaRow(db, 'id', hit.id, 'detail');
  return { lat, lon, area: parse(hit.summary), breadcrumb: detail.breadcrumb, resolved_levels: levels };
}

async function nearby(db: D1Database, lat: number, lon: number, radius: number, cat: string | undefined, limit: number) {
  const dLat = radius / 111_000;
  const dLon = radius / (111_000 * Math.cos((lat * Math.PI) / 180));
  const { results } = await db.prepare('SELECT id, lat, lon, category_key, subcategory_key, summary FROM place_points WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?')
    .bind(lat - dLat, lat + dLat, lon - dLon, lon + dLon)
    .all<{ id: number; lat: number; lon: number; category_key: string; subcategory_key: string | null; summary: string }>();
  return results
    .filter((r) => !cat || r.category_key === cat || r.subcategory_key === cat)
    .map((r) => ({ id: r.id, d: distanceM(lat, lon, r.lat, r.lon), s: r.summary }))
    .filter((r) => r.d <= radius)
    .sort((a, b) => a.d - b.d || a.id - b.id)
    .slice(0, limit)
    .map((r) => ({ ...parse<Record<string, unknown>>(r.s), distance_m: Math.round(r.d) }));
}

async function geojson(db: D1Database, areaId: number | undefined, cat: string | undefined, bbox: number[] | null) {
  const [w, s, e, n] = bbox ?? [-180, -90, 180, 90];
  const area = areaId
    ? ' AND (division_id = ?5 OR district_id = ?5 OR upazila_id = ?5 OR union_id = ?5 OR city_corporation_id = ?5)' : '';
  const stmt = db.prepare(`SELECT lat, lon, category_key, subcategory_key, summary FROM place_points
    WHERE lat BETWEEN ?1 AND ?2 AND lon BETWEEN ?3 AND ?4${area} LIMIT 5000`);
  const { results } = await (areaId ? stmt.bind(s, n, w, e, areaId) : stmt.bind(s, n, w, e))
    .all<{ lat: number; lon: number; category_key: string; subcategory_key: string | null; summary: string }>();
  return {
    type: 'FeatureCollection',
    features: results.filter((r) => !cat || r.category_key === cat || r.subcategory_key === cat).map((r) => {
      const { lat: _la, lon: _lo, ...props } = parse<Record<string, unknown>>(r.summary);
      return { type: 'Feature', geometry: { type: 'Point', coordinates: [r.lon, r.lat] }, properties: props };
    }),
  };
}

/* ---------------------------------------------------------------- contact form */

function visitorIp(req: Request, env: Env): string | null {
  const key = env.EDGE_SHARED_SECRET;
  const sent = req.headers.get('x-edge-key');
  const ip = req.headers.get('x-edge-client-ip');
  if (key && key.length >= 32 && sent === key && ip && IP_RE.test(ip)) return ip;   // from our website (service binding)
  return req.headers.get('cf-connecting-ip');
}
async function sha256(s: string) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 32);
}
function textField(b: Record<string, unknown>, key: string, o: { max: number; min?: number; required?: boolean }): string | null {
  const v = b[key];
  if (v === undefined || v === null || v === '') { if (o.required) throw bad(`${key} is required`); return null; }
  if (typeof v !== 'string') throw bad(`${key} must be text`);
  const s = v.normalize('NFC').trim();
  if (o.min && s.length < o.min) throw bad(`${key} must be at least ${o.min} characters`);
  if (s.length > o.max) throw bad(`${key} must be at most ${o.max} characters`);
  return s;
}
async function contact(req: Request, env: Env) {
  const raw = await req.text();
  if (raw.length > 8 * 1024) throw new HttpError(413, 'Payload Too Large', 'message too large');
  let b: Record<string, unknown>;
  try { b = JSON.parse(raw) as Record<string, unknown>; } catch { throw bad('body must be JSON'); }
  if (!b || typeof b !== 'object' || Array.isArray(b)) throw bad('body must be a JSON object');
  if (typeof b.website === 'string' && b.website) return { received: true };   // honeypot
  const subject = textField(b, 'subject', { max: 120, min: 3, required: true });
  const message = textField(b, 'message', { max: 1000, min: 10, required: true });
  const email = textField(b, 'email', { max: 120 });
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw bad('email looks invalid');
  const ip = visitorIp(req, env);
  const ipHash = ip ? await sha256(`${ip}|${env.EDGE_SHARED_SECRET ?? 'elaka360'}`) : null;
  if (ipHash) {
    const recent = await env.DB.prepare(
      "SELECT count(*) AS n FROM contact_messages WHERE ip_hash = ? AND created_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 hour')")
      .bind(ipHash).first<{ n: number }>();
    if ((recent?.n ?? 0) >= 5) throw new HttpError(429, 'Too Many Requests', 'too many messages; try again later');
  }
  await env.DB.prepare('INSERT INTO contact_messages(email, subject, message, ip_hash) VALUES (?, ?, ?, ?)').bind(email, subject, message, ipHash).run();
  return { received: true };
}

/* ---------------------------------------------------------------- routing */

type Handler = (m: string[], url: URL, req: Request, env: Env) => Promise<unknown>;
const GET: [RegExp, Handler][] = [
  [/^\/health$/, async (_m, _u, _r, env) => {
    const t = Date.now();
    await env.DB.prepare('SELECT 1').first();
    return { status: 'ok', db: { ok: true, ms: Date.now() - t }, search: { engine: 'browser', configured: false },
      public_include_unverified: true, staff_require_2fa: true, version: env.APP_VERSION ?? 'dev' };
  }],
  [/^\/v1\/stats\/national$/, (_m, _u, _r, env) => meta(env.DB, 'stats:national')],
  [/^\/v1\/categories$/, (_m, _u, _r, env) => meta(env.DB, 'categories')],
  [/^\/v1\/categories\/([a-z_.]{2,82})$/, async (m, _u, _r, env) => {
    const all = await meta<{ key: string; children?: { key: string }[] }[]>(env.DB, 'categories');
    const found = all.find((c) => c.key === m[1]) ?? all.flatMap((c) => c.children ?? []).find((c) => c.key === m[1]);
    if (!found) throw notFound(`category not found: ${m[1]}`);
    return found;
  }],
  [/^\/v1\/emergency-numbers$/, (_m, _u, _r, env) => meta(env.DB, 'emergency')],
  [/^\/v1\/areas$/, async (_m, u, _r, env) => {
    const level = u.searchParams.get('level') ?? 'division';
    if (!LEVELS.has(level)) throw bad(`level must be one of ${[...LEVELS].join(', ')}`);
    const limit = intParam(u.searchParams.get('limit'), 'limit', { min: 1, max: 500, def: 100 })!;
    const offset = cursor.decode(u.searchParams.get('cursor'));
    const parent = intParam(u.searchParams.get('parent_id'), 'parent_id', { min: 1 });
    const stmt = parent
      ? env.DB.prepare('SELECT summary FROM areas WHERE level = ? AND parent_id = ? ORDER BY name_en LIMIT ? OFFSET ?').bind(level, parent, limit, offset)
      : env.DB.prepare('SELECT summary FROM areas WHERE level = ? ORDER BY name_en LIMIT ? OFFSET ?').bind(level, limit, offset);
    const items = (await stmt.all<{ summary: string }>()).results.map((r) => parse(r.summary));
    return { items, next_cursor: items.length === limit ? cursor.encode(offset + limit) : null };
  }],
  [/^\/v1\/areas\/by-path$/, (_m, u, _r, env) => areaRow(env.DB, 'path', normalisePath(u.searchParams.get('path')), 'detail')],
  [/^\/v1\/areas\/tree$/, (_m, u, _r, env) => tree(env.DB,
    intParam(u.searchParams.get('root_id'), 'root_id', { min: 1, def: 1 })!, intParam(u.searchParams.get('depth'), 'depth', { min: 1, max: 3, def: 2 })!)],
  [/^\/v1\/areas\/([^/]+)$/, (m, _u, _r, env) => areaRow(env.DB, 'id', idParam(m[1]), 'detail')],
  [/^\/v1\/areas\/([^/]+)\/children$/, async (m, u, _r, env) => {
    const level = u.searchParams.get('level');
    if (level && !LEVELS.has(level)) throw bad('invalid level');
    const d = await areaRow(env.DB, 'id', idParam(m[1]), 'detail');
    return (d.children as { level: string }[]).filter((c) => !level || c.level === level);
  }],
  [/^\/v1\/areas\/([^/]+)\/stats$/, (m, _u, _r, env) => areaRow(env.DB, 'id', idParam(m[1]), 'stats')],
  [/^\/v1\/areas\/([^/]+)\/boundary$/, async (m, _u, _r, env) => {
    const id = idParam(m[1]);
    const row = await env.DB.prepare('SELECT summary, geometry FROM boundaries WHERE id = ?').bind(id).first<{ summary: string; geometry: string }>();
    if (!row) throw notFound(`no public boundary for area ${id}`);
    const s = parse<{ id: number; name_bn: string; name_en: string; level: string }>(row.summary);
    return { type: 'Feature', id, properties: { id, name_bn: s.name_bn, name_en: s.name_en, level: s.level }, geometry: parse(row.geometry) };
  }],
  [/^\/v1\/geo\/locate$/, (_m, u, _r, env) => locate(env.DB, floatParam(u.searchParams.get('lat'), 'lat', 20, 27), floatParam(u.searchParams.get('lon'), 'lon', 88, 93))],
  [/^\/v1\/places$/, async (_m, u, _r, env) => {
    const limit = intParam(u.searchParams.get('limit'), 'limit', { min: 1, max: 100, def: 20 })!;
    const offset = cursor.decode(u.searchParams.get('cursor'));
    const sort = u.searchParams.get('sort');
    if (sort && sort !== 'relevance' && sort !== 'name') throw bad('sort must be relevance or name');
    if (u.searchParams.get('q')) throw bad('text search runs in the browser on this deployment (see /search)');
    const { items, total } = await placeList(env.DB, intParam(u.searchParams.get('area_id'), 'area_id', { min: 1 }),
      category(u.searchParams.get('category')), limit, offset);
    return { items, total, next_cursor: offset + items.length < total ? cursor.encode(offset + limit) : null };
  }],
  [/^\/v1\/places\/nearby$/, async (_m, u, _r, env) => ({
    items: await nearby(env.DB, floatParam(u.searchParams.get('lat'), 'lat', 20, 27), floatParam(u.searchParams.get('lon'), 'lon', 88, 93),
      intParam(u.searchParams.get('radius_m'), 'radius_m', { min: 100, max: 50000, def: 2000 })!, category(u.searchParams.get('category')),
      intParam(u.searchParams.get('limit'), 'limit', { min: 1, max: 100, def: 30 })!),
    next_cursor: null,
  })],
  [/^\/v1\/places\/geojson$/, (_m, u, _r, env) => {
    const raw = u.searchParams.get('bbox');
    let box: number[] | null = null;
    if (raw) {
      const n = raw.split(',').map(Number);
      if (n.length !== 4 || n.some((x) => !Number.isFinite(x)) || n[0]! >= n[2]! || n[1]! >= n[3]!) throw bad('bbox must be west,south,east,north');
      box = n;
    }
    return geojson(env.DB, intParam(u.searchParams.get('area_id'), 'area_id', { min: 1 }), category(u.searchParams.get('category')), box);
  }],
  [/^\/v1\/places\/([^/]+)$/, async (m, _u, _r, env) => {
    if (!SLUG_RE.test(m[1]!)) throw bad('invalid slug');
    const row = await env.DB.prepare('SELECT detail FROM places WHERE slug = ?').bind(m[1]).first<{ detail: string }>();
    if (!row) throw notFound(`place not found: ${m[1]}`);
    return parse(row.detail);
  }],
  [/^\/v1\/places\/([^/]+)\/reviews$/, async (m, _u, _r, env) => {
    if (!SLUG_RE.test(m[1]!)) throw bad('invalid slug');
    const row = await env.DB.prepare('SELECT id FROM places WHERE slug = ?').bind(m[1]).first();
    if (!row) throw notFound(`place not found: ${m[1]}`);
    return { items: [], next_cursor: null };   // reviews need accounts, which are not served on this deployment yet
  }],
];
/** Features that need accounts or the database's write side: not on this deployment yet. */
const UNAVAILABLE = /^\/v1\/(auth|me|contributions|admin|open-data|reviews|search)(\/|$)|^\/v1\/places\/[^/]+\/reviews$/;

function problem(status: number, title: string, detail: string, path: string, requestId: string, extra: Record<string, string> = {}) {
  return new Response(JSON.stringify({ type: 'about:blank', title, status, detail, instance: path, request_id: requestId }), {
    status, headers: { 'content-type': 'application/problem+json', 'cache-control': 'no-store', 'x-request-id': requestId, ...extra },
  });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';
    const requestId = req.headers.get('x-request-id')?.match(/^[A-Za-z0-9._-]{8,64}$/)?.[0] ?? crypto.randomUUID();
    try {
      if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'GET', 'access-control-max-age': '86400' } });
      let body: unknown;
      if (req.method === 'GET' || req.method === 'HEAD') {
        const route = GET.find(([re]) => re.test(path));
        if (!route) {
          if (UNAVAILABLE.test(path)) throw new HttpError(503, 'Service Unavailable', 'This feature needs sign-in, which is not available yet.');
          throw notFound(`no route for GET ${path}`);
        }
        body = await route[1](path.match(route[0]) as string[], url, req, env);
      } else if (req.method === 'POST' && path === '/v1/contact') {
        return Response.json(await contact(req, env), { status: 201, headers: { 'cache-control': 'no-store', 'x-request-id': requestId } });
      } else if (UNAVAILABLE.test(path)) {
        throw new HttpError(503, 'Service Unavailable', 'Sign-in, reviews and contributions are not available yet.');
      } else {
        throw new HttpError(405, 'Method Not Allowed', `${req.method} ${path}`);
      }
      return new Response(JSON.stringify(body), {
        headers: {
          'content-type': 'application/json; charset=utf-8', 'x-request-id': requestId, 'access-control-allow-origin': '*',
          'cache-control': path === '/health' ? 'no-store' : 'public, max-age=300, stale-while-revalidate=3600',
        },
      });
    } catch (e) {
      if (e instanceof HttpError) return problem(e.status, e.title, e.message, path, requestId);
      console.error(JSON.stringify({ request_id: requestId, path, error: (e as Error).message }));
      return problem(500, 'Internal Server Error', 'unexpected error', path, requestId);
    }
  },
};
