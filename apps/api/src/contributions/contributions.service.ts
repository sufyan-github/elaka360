import { BadRequestException, HttpException, HttpStatus, Injectable, NotFoundException } from '@nestjs/common';
import type { Contribution, ContributionStatus, ContributionType } from '@elaka360/shared';
import { Db, audit, type Queryable } from '../db/db.service';
import { LOCATE_SQL } from '../geo/geo.sql';
import { enumField, normalisePath, textField, urlField } from '../common/params';
import { findDuplicates, recordDuplicates } from '../quality/duplicates';

export const TYPES: ContributionType[] = ['new_place', 'new_business', 'new_tourist_spot', 'area_info', 'photo', 'correction', 'report'];

export const CONTRIBUTION_COLS = `
c.id::int, c.type::text, c.status::text, p.slug AS target_place_slug, c.target_area_id::int, c.payload, c.evidence,
c.lat::float8, c.lon::float8, c.confirmed_accurate, c.reviewer_note,
to_char(c.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at, to_char(c.updated_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS updated_at,
to_char(c.reviewed_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS reviewed_at`;

export const EVENTS_SQL = `
SELECT e.from_status::text, e.to_status::text, e.note, u.name AS actor_name, to_char(e.at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS at
FROM contribution_events e LEFT JOIN users u ON u.id = e.actor_id WHERE e.contribution_id = $1 ORDER BY e.at, e.id`;

const PLACE_TYPES = new Set<ContributionType>(['new_place', 'new_business', 'new_tourist_spot']);

/** Validate the submitted fields for a contribution type. Never trusts client-side checks. */
export function validatePayload(type: ContributionType, raw: unknown): Record<string, unknown> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new BadRequestException('payload must be an object');
  const p = raw as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  const put = (k: string, max: number, required = false, min?: number) => {
    const v = textField(p, k, { max, required, min });
    if (v !== null) out[k] = v;
  };
  if (PLACE_TYPES.has(type)) {
    put('name_bn', 120, true, 2);
    put('name_en', 120);
    put('category_key', 60, true);
    if (!/^[a-z_]{2,40}(\.[a-z_]{2,40})?$/.test(String(out.category_key))) throw new BadRequestException('invalid category_key');
    put('ownership', 20);
    put('address', 200);
    put('description', 500);
    put('website', 300);
    if (out.website) out.website = urlField(out.website, 'website');
    if (p.phones !== undefined) {
      if (!Array.isArray(p.phones) || p.phones.length > 5) throw new BadRequestException('phones must be a list of up to 5');
      out.phones = p.phones.map((x) => {
        if (typeof x !== 'string' || !/^\+?[0-9০-৯\- ]{5,20}$/.test(x)) throw new BadRequestException('invalid phone');
        return x.trim();
      });
    }
  } else if (type === 'correction' || type === 'report' || type === 'area_info') {
    put('field', 60);
    put('current_value', 500);
    put('proposed_value', 500, type === 'correction');
    put('note', 1000, type !== 'correction', 5);
  } else if (type === 'photo') {
    put('caption', 200);
    put('note', 500);
  }
  return out;
}

export function validateEvidence(raw: unknown): { url: string; note?: string }[] {
  if (raw === undefined || raw === null) return [];
  if (!Array.isArray(raw) || raw.length > 5) throw new BadRequestException('evidence must be a list of up to 5 links');
  return raw.map((e, i) => {
    if (!e || typeof e !== 'object') throw new BadRequestException(`evidence[${i}] must be {url, note}`);
    const o = e as Record<string, unknown>;
    const note = textField(o, 'note', { max: 300 });
    return { url: urlField(o.url, `evidence[${i}].url`), ...(note ? { note } : {}) };
  });
}

/** Flag likely duplicates of a submitted new-place suggestion for staff review. */
async function flagDuplicates(q: Queryable, id: number) {
  const c = await q.one<{ type: ContributionType; payload: Record<string, unknown>; lat: number | null; lon: number | null }>(
    'SELECT type::text, payload, lat::float8, lon::float8 FROM contributions WHERE id = $1', [id]);
  if (!c || !PLACE_TYPES.has(c.type) || typeof c.payload.name_bn !== 'string') return;
  const cat = await q.one<{ top: number }>('SELECT COALESCE(parent_id, id) AS top FROM categories WHERE key = $1', [String(c.payload.category_key)]);
  if (!cat) return;
  const m = await findDuplicates(q, { name_bn: c.payload.name_bn, name_en: typeof c.payload.name_en === 'string' ? c.payload.name_en : null, categoryId: cat.top, lat: c.lat, lon: c.lon });
  await recordDuplicates(q, m, { contributionId: id });
}

@Injectable()
export class ContributionsService {
  constructor(private readonly db: Db) {}

  async create(userId: number, b: Record<string, unknown>): Promise<Contribution> {
    const type = enumField(b, 'type', TYPES)!;
    const payload = validatePayload(type, b.payload);
    const evidence = validateEvidence(b.evidence);
    const submit = b.submit === true;
    const confirmed = b.confirmed_accurate === true;
    if (submit && !confirmed) throw new BadRequestException('confirm the information is accurate before submitting');
    const { lat, lon } = coords(b);
    const day = await this.db.one<{ n: number }>(`SELECT count(*)::int AS n FROM contributions WHERE user_id = $1 AND created_at > now() - interval '1 day'`, [userId]);
    if ((day?.n ?? 0) >= 20) throw new HttpException('daily contribution limit reached', HttpStatus.TOO_MANY_REQUESTS);

    return this.db.tx(async (q) => {
      const target = await this.target(q, type, b, lat, lon);
      const status: ContributionStatus = submit ? 'new' : 'draft';
      const row = await q.one<{ id: number }>(
        `INSERT INTO contributions(user_id, type, target_place_id, target_area_id, payload, evidence, lat, lon, confirmed_accurate, status, area_path)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING id::int`,
        [userId, type, target.placeId, target.areaId, JSON.stringify(payload), JSON.stringify(evidence), lat, lon, confirmed, status, target.path]);
      await q.many(`INSERT INTO contribution_events(contribution_id, actor_id, from_status, to_status) VALUES ($1,$2,NULL,$3)`, [row!.id, userId, status]);
      await audit(q, { actor: userId, action: submit ? 'contribution.submit' : 'contribution.draft', entity: 'contribution', entityId: row!.id });
      if (submit) await flagDuplicates(q, row!.id);
      return this.get(row!.id, userId, q);
    });
  }

  async update(id: number, userId: number, b: Record<string, unknown>): Promise<Contribution> {
    return this.db.tx(async (q) => {
      const cur = await q.one<{ type: ContributionType; status: ContributionStatus; user_id: number }>(
        'SELECT type::text, status::text, user_id::int FROM contributions WHERE id = $1 FOR UPDATE', [id]);
      if (!cur || cur.user_id !== userId) throw new NotFoundException('contribution not found');
      if (cur.status !== 'draft' && cur.status !== 'needs_changes') throw new BadRequestException('only drafts and returned submissions can be edited');
      const payload = b.payload === undefined ? undefined : validatePayload(cur.type, b.payload);
      const evidence = b.evidence === undefined ? undefined : validateEvidence(b.evidence);
      const { lat, lon } = coords(b);
      await q.many(
        `UPDATE contributions SET payload = COALESCE($2, payload), evidence = COALESCE($3, evidence),
           lat = COALESCE($4, lat), lon = COALESCE($5, lon),
           confirmed_accurate = COALESCE($6, confirmed_accurate), updated_at = now() WHERE id = $1`,
        [id, payload ? JSON.stringify(payload) : null, evidence ? JSON.stringify(evidence) : null, lat, lon,
         typeof b.confirmed_accurate === 'boolean' ? b.confirmed_accurate : null]);
      return this.get(id, userId, q);
    });
  }

  async submit(id: number, userId: number): Promise<Contribution> {
    return this.db.tx(async (q) => {
      const cur = await q.one<{ status: ContributionStatus; user_id: number; confirmed_accurate: boolean }>(
        'SELECT status::text, user_id::int, confirmed_accurate FROM contributions WHERE id = $1 FOR UPDATE', [id]);
      if (!cur || cur.user_id !== userId) throw new NotFoundException('contribution not found');
      if (cur.status !== 'draft' && cur.status !== 'needs_changes') throw new BadRequestException('already submitted');
      if (!cur.confirmed_accurate) throw new BadRequestException('confirm the information is accurate before submitting');
      await q.many(`UPDATE contributions SET status = 'new', updated_at = now() WHERE id = $1`, [id]);
      await q.many(`INSERT INTO contribution_events(contribution_id, actor_id, from_status, to_status) VALUES ($1,$2,$3,'new')`, [id, userId, cur.status]);
      await audit(q, { actor: userId, action: 'contribution.submit', entity: 'contribution', entityId: id });
      await flagDuplicates(q, id);
      return this.get(id, userId, q);
    });
  }

  async get(id: number, userId: number | null, q: Queryable = this.db): Promise<Contribution> {
    const row = await q.one<Contribution & { user_id: number }>(
      `SELECT ${CONTRIBUTION_COLS}, c.user_id::int FROM contributions c LEFT JOIN places p ON p.id = c.target_place_id WHERE c.id = $1`, [id]);
    if (!row || (userId !== null && row.user_id !== userId)) throw new NotFoundException('contribution not found');
    const { user_id: _u, ...c } = row;
    return { ...c, events: await q.many(EVENTS_SQL, [id]) };
  }

  mine(userId: number) {
    return this.db.many<Contribution>(
      `SELECT ${CONTRIBUTION_COLS} FROM contributions c LEFT JOIN places p ON p.id = c.target_place_id
       WHERE c.user_id = $1 ORDER BY c.created_at DESC LIMIT 200`, [userId]);
  }

  async stats(userId: number) {
    const rows = await this.db.many<{ status: string; n: number }>(
      'SELECT status::text, count(*)::int AS n FROM contributions WHERE user_id = $1 GROUP BY status', [userId]);
    return Object.fromEntries(rows.map((r) => [r.status, r.n]));
  }

  /** Resolve the target record and the area path used for scoped moderation. */
  private async target(q: Queryable, type: ContributionType, b: Record<string, unknown>, lat: number | null, lon: number | null) {
    let placeId: number | null = null;
    let areaId: number | null = null;
    let path: string | null = null;
    if (typeof b.target_place_slug === 'string') {
      const p = await q.one<{ id: number; path: string | null }>(
        `SELECT p.id::int, a.path FROM public_places p LEFT JOIN admin_areas a ON a.id = COALESCE(p.union_id, p.upazila_id, p.city_corporation_id, p.district_id)
         WHERE p.slug = $1`, [b.target_place_slug]);
      if (!p) throw new NotFoundException('target place not found');
      placeId = p.id;
      path = p.path;
    } else if (typeof b.target_area_path === 'string') {
      const a = await q.one<{ id: number; path: string }>('SELECT id::int, path FROM public_admin_areas WHERE path = $1', [normalisePath(b.target_area_path)]);
      if (!a) throw new NotFoundException('target area not found');
      areaId = a.id;
      path = a.path;
    } else if (lat !== null && lon !== null) {
      path = (await q.one<{ path: string }>(LOCATE_SQL, [lat, lon]))?.path ?? null;
    }
    if ((type === 'correction' || type === 'photo' || type === 'report') && !placeId && !areaId) {
      throw new BadRequestException('target_place_slug or target_area_path is required for this type');
    }
    return { placeId, areaId, path };
  }
}

function coords(b: Record<string, unknown>): { lat: number | null; lon: number | null } {
  if (b.lat == null && b.lon == null) return { lat: null, lon: null };
  const lat = Number(b.lat);
  const lon = Number(b.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < 20.3 || lat > 26.8 || lon < 88 || lon > 92.8) {
    throw new BadRequestException('lat/lon must be inside Bangladesh');
  }
  return { lat: Math.round(lat * 1e6) / 1e6, lon: Math.round(lon * 1e6) / 1e6 };
}
