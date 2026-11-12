/**
 * Search that runs in the browser over the static index in /data/search/*.json (written by
 * apps/api/src/cli/export-edge.ts). On the Cloudflare free plan this keeps search off D1, whose daily row-read
 * allowance a server-side substring search would use up quickly. Matching mirrors the API's Postgres search
 * (apps/api/src/search/search.sql.ts, places.sql.ts): word prefixes, the Banglish key, all terms must match.
 */
import type { AdminAreaSummary, AdminLevel, EvidenceLevel, PlaceSummary } from '@elaka360/shared';
import { latinKey } from '@elaka360/shared';

interface Table { fields: string[]; rows: unknown[][] }
interface PlaceIndex { fields: string[]; rows: unknown[][]; cats: string[]; ev: EvidenceLevel[] }
interface AreaEntry extends AdminAreaSummary { bn: string; en: string; key: string }
interface PlaceEntry { summary: PlaceSummary; bn: string; en: string; key: string }

const LEVEL_RANK: AdminLevel[] = ['division', 'district', 'city_corporation', 'upazila', 'pourashava', 'union'];
const rank = (l: AdminLevel) => { const i = LEVEL_RANK.indexOf(l); return i < 0 ? 99 : i; };

let areasP: Promise<{ list: AreaEntry[]; byId: Map<number, AreaEntry> }> | null = null;
let placesP: Promise<PlaceEntry[]> | null = null;

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return (await res.json()) as T;
}

function loadAreas() {
  areasP ??= getJson<Table>('/data/search/areas.json').then(({ fields, rows }) => {
    const list = rows.map((r) => {
      const a = Object.fromEntries(fields.map((f, i) => [f, r[i]])) as unknown as AdminAreaSummary;
      return { ...a, bn: (a.name_bn ?? '').normalize('NFC'), en: (a.name_en ?? '').toLowerCase(), key: latinKey(a.name_en ?? '') };
    });
    return { list, byId: new Map(list.map((a) => [a.id, a])) };
  }).catch((e) => { areasP = null; throw e; });
  return areasP;
}

function loadPlaces() {
  placesP ??= Promise.all([loadAreas(), getJson<PlaceIndex>('/data/search/places.json')]).then(([{ byId }, idx]) => {
    const f = Object.fromEntries(idx.fields.map((n, i) => [n, i])) as Record<string, number>;
    return idx.rows.map((r) => {
      const cat = idx.cats[r[f.cat!] as number] ?? 'other';
      const loc = byId.get(r[f.loc_id!] as number);
      const dist = byId.get(r[f.district_id!] as number);
      const ev = idx.ev[r[f.ev!] as number] ?? 'unverified';
      const nameEn = (r[f.name_en!] as string | null) ?? null;
      const summary: PlaceSummary = {
        public_id: r[f.slug!] as string, slug: r[f.slug!] as string, name_bn: r[f.name_bn!] as string, name_en: nameEn,
        category_key: cat.split('.')[0]!, subcategory_key: cat.includes('.') ? cat : null,
        area_label_bn: [loc?.name_bn, dist?.name_bn].filter(Boolean).join(', ') || null,
        area_label_en: [loc?.name_en, dist?.name_en].filter(Boolean).join(', ') || null,
        lat: null, lon: null, verification_status: 'unverified', evidence_level: ev,
        production_eligible: ev === 'official' || ev === 'secondary',
      };
      return { summary, bn: summary.name_bn.normalize('NFC'), en: (nameEn ?? '').toLowerCase(), key: latinKey(nameEn ?? '') };
    });
  }).catch((e) => { placesP = null; throw e; });
  return placesP;
}

/** Same clean-up as the API's searchText(): NFC, no LIKE wildcards, single spaces. */
export function cleanQuery(raw: string): string {
  return raw.normalize('NFC').replace(/[%_\\]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 80);
}
const isLatin = (q: string) => /[a-z]/i.test(q);
const wordPrefix = (text: string, q: string) => text.startsWith(q) || text.includes(` ${q}`);

export interface BrowserSearchResult { areas: AdminAreaSummary[]; places: PlaceSummary[] }

export async function search(raw: string, o: { type?: 'area' | 'place'; limit?: number } = {}): Promise<BrowserSearchResult> {
  const q = cleanQuery(raw);
  const limit = o.limit ?? 20;
  if (q.length < 2) return { areas: [], places: [] };
  const ql = q.toLowerCase();
  const key = isLatin(q) ? latinKey(q) : '';
  const [areas, places] = await Promise.all([
    o.type === 'place' ? [] : loadAreas().then(({ list }) => list
      .filter((a) => a.level !== 'country' && (wordPrefix(a.bn, q) || wordPrefix(a.en, ql)
        || (key !== '' && (a.key.startsWith(key) || (key.length >= 4 && a.key.includes(key)))) || (q.length >= 3 && a.bn.includes(q))))
      .map((a) => ({ a, exact: a.key === key || a.bn === q || a.en === ql ? 0 : 1 }))
      .sort((x, y) => x.exact - y.exact || rank(x.a.level) - rank(y.a.level) || x.a.en.localeCompare(y.a.en))
      .slice(0, limit)
      .map(({ a }) => strip(a))),
    o.type === 'area' ? [] : loadPlaces().then((list) => {
      const terms = [...new Set(ql.split(' ').filter(Boolean))].slice(0, 5).map((t) => ({ t, k: isLatin(t) ? latinKey(t) : '' }));
      const out: PlaceSummary[] = [];
      // the index is stored in the API's list order (evidence, then English name, then Bangla name)
      for (const p of list) {
        if (terms.every(({ t, k }) => p.bn.includes(t) || p.en.includes(t) || (k !== '' && p.key.includes(k)))) out.push(p.summary);
        if (out.length >= limit) break;
      }
      return out;
    }),
  ]);
  return { areas, places };
}

export interface Suggestion { kind: 'area' | 'place'; name_bn: string; name_en: string; href_key: string; detail: string }

/** Prefix suggestions for the search box: areas first (by level), then places. Areas load fast; places follow. */
export async function suggest(raw: string, limit = 8): Promise<Suggestion[]> {
  const q = cleanQuery(raw);
  if (q.length < 2) return [];
  const ql = q.toLowerCase();
  const key = isLatin(q) ? latinKey(q) : '';
  const { list } = await loadAreas();
  const areas = list
    .filter((a) => a.level !== 'country' && (a.bn.startsWith(q) || a.en.startsWith(ql) || (key !== '' && a.key.startsWith(key))))
    .sort((x, y) => rank(x.level) - rank(y.level) || x.en.localeCompare(y.en))
    .slice(0, limit)
    .map((a): Suggestion => ({ kind: 'area', name_bn: a.name_bn, name_en: a.name_en, href_key: a.path, detail: a.level }));
  if (areas.length >= limit) return areas;
  const places = (await loadPlaces())
    .filter((p) => p.bn.startsWith(q) || p.en.startsWith(ql) || (key !== '' && p.key.startsWith(key)))
    .sort((x, y) => x.en.localeCompare(y.en))
    .slice(0, limit - areas.length)
    .map((p): Suggestion => ({ kind: 'place', name_bn: p.summary.name_bn, name_en: p.summary.name_en ?? '', href_key: p.summary.slug, detail: p.summary.evidence_level }));
  return [...areas, ...places];
}

function strip(a: AreaEntry): AdminAreaSummary {
  const { bn: _b, en: _e, key: _k, ...summary } = a;
  return summary;
}
