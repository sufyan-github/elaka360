import { BadRequestException, Body, Controller, Get, NotFoundException, Param, Patch, Post, Query, Req } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { AuditEntry } from '@elaka360/shared';
import { Db, audit, type Queryable } from '../db/db.service';
import { CurrentUser, RequireAuth, assertInScope, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { body, floatParam, idParam, intParam, textField, urlField } from '../common/params';
import * as Q from './admin.sql';
import { EVIDENCE, boolQuery, page, paged, readVerify } from './admin.util';
import { findDuplicates, recordDuplicates } from '../quality/duplicates';
import { DUP_BLOCKING_SQL } from '../quality/duplicates.sql';

const STATUSES = ['draft', 'active', 'inactive', 'closed', 'archived'];
const OWNERSHIP = ['public', 'private', 'ngo', 'trust', 'autonomous'];

function slugify(s: string) {
  return s.toLowerCase().replace(/'/g, '').replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80);
}

/** Resolve the five area FKs of a place from its most specific admin area. */
export async function areaFks(q: Queryable, areaId: number) {
  const chain = await q.many<{ id: number; level: string; path: string }>(
    `WITH RECURSIVE up AS (SELECT id, level, parent_id, path FROM admin_areas WHERE id = $1
       UNION ALL SELECT a.id, a.level, a.parent_id, a.path FROM admin_areas a JOIN up ON a.id = up.parent_id)
     SELECT id::int, level::text, path FROM up`, [areaId]);
  if (!chain.length) throw new BadRequestException('unknown area_id');
  const by = (l: string) => chain.find((c) => c.level === l)?.id ?? null;
  return { division_id: by('division'), district_id: by('district'), upazila_id: by('upazila'), union_id: by('union'),
           city_corporation_id: by('city_corporation'), path: chain[0]!.path };
}

/** Category id + optional subcategory id from a key like "health" or "health.hospital". */
export async function categoryIds(q: Queryable, key: string) {
  const row = await q.one<{ id: number; parent_id: number | null }>('SELECT id, parent_id FROM categories WHERE key = $1', [key]);
  if (!row) throw new BadRequestException('unknown category');
  return row.parent_id ? { category_id: row.parent_id, subcategory_id: row.id } : { category_id: row.id, subcategory_id: null };
}

@ApiTags('admin')
@Controller('v1/admin')
export class AdminPlacesController {
  constructor(private readonly db: Db) {}

  @Get('places')
  @RequireAuth('places.read')
  async list(
    @CurrentUser() u: AuthUser, @Query('q') q?: string, @Query('category') cat?: string, @Query('evidence') ev?: string,
    @Query('eligible') el?: string, @Query('status') st?: string, @Query('limit') l?: string, @Query('cursor') c?: string,
  ) {
    if (ev && !EVIDENCE.includes(ev as never)) throw new BadRequestException('invalid evidence');
    if (st && !STATUSES.includes(st)) throw new BadRequestException('invalid status');
    const { limit, offset } = page(l, c);
    const rows = await this.db.many<{ total: number }>(Q.ADMIN_PLACE_LIST_SQL,
      [q?.trim().slice(0, 80) || null, cat || null, ev || null, boolQuery(el), st || null, u.scope_path, limit, offset]);
    return paged(rows, limit, offset);
  }

  @Get('places/:id')
  @RequireAuth('places.read')
  async get(@CurrentUser() u: AuthUser, @Param('id') id: string) {
    const place = await this.db.one<{ area_path: string | null; id: number }>(Q.ADMIN_PLACE_SQL, [idParam(id)]);
    if (!place) throw new NotFoundException('place not found');
    assertInScope(u, place.area_path);
    const history = await this.db.many<AuditEntry>(Q.AUDIT_LIST_SQL, ['place', String(place.id), null, 50, 0]);
    return { ...place, history };
  }

  @Post('places')
  @RequireAuth('places.edit')
  @ApiOperation({ summary: 'Create a place. It starts unverified and unpublished; publish through /verify.' })
  async create(@CurrentUser() u: AuthUser, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    return this.db.tx(async (q) => {
      const f = await this.fields(q, b, true);
      assertInScope(u, f.area?.path ?? null);
      const seq = await q.one<{ n: number }>("SELECT nextval('places_id_seq')::int AS n");
      const prefix = f.cat!.key.startsWith('tourism') ? 'TOUR' : f.cat!.key.startsWith('business') ? 'BIZ' : 'INST';
      const publicId = `${prefix}-${String(seq!.n).padStart(8, '0')}`;
      let slug = slugify(String(f.v.name_en ?? '')) || publicId.toLowerCase();
      if (await q.one('SELECT 1 AS x FROM places WHERE slug = $1', [slug])) slug = `${slug}-${seq!.n}`;
      const row = await q.one<{ id: number }>(
        `INSERT INTO places(id, public_id, slug, name_bn, name_en, short_name, category_id, subcategory_id, ownership,
           division_id, district_id, upazila_id, union_id, city_corporation_id, address_bn, address_en, postcode, lat, lon,
           phones, email, website, established, description_bn, description_en, opening_hours, data_source_id, source_notes,
           status, created_by)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,'active',$29)
         RETURNING id::int`,
        [seq!.n, publicId, slug, f.v.name_bn, f.v.name_en, f.v.short_name, f.cat!.category_id, f.cat!.subcategory_id, f.v.ownership,
         f.area?.division_id ?? null, f.area?.district_id ?? null, f.area?.upazila_id ?? null, f.area?.union_id ?? null, f.area?.city_corporation_id ?? null,
         f.v.address_bn, f.v.address_en, f.v.postcode, f.v.lat, f.v.lon, f.v.phones ?? [], f.v.email, f.v.website, f.v.established,
         f.v.description_bn, f.v.description_en, f.v.opening_hours ? JSON.stringify(f.v.opening_hours) : null, f.v.data_source_id, f.v.source_notes, u.id]);
      const dups = await findDuplicates(q, { name_bn: String(f.v.name_bn), name_en: (f.v.name_en as string | null) ?? null, categoryId: f.cat!.category_id,
                                            lat: (f.v.lat as number | null) ?? null, lon: (f.v.lon as number | null) ?? null, excludeId: row!.id });
      await recordDuplicates(q, dups, { placeId: row!.id });
      const after = await q.one(Q.ADMIN_PLACE_SQL, [row!.id]);
      await audit(q, { actor: u.id, action: 'place.create', entity: 'place', entityId: row!.id, after, requestId: req.id, ip: req.ip });
      return { ...(after as object), possible_duplicates: dups };
    });
  }

  @Patch('places/:id')
  @RequireAuth('places.edit')
  @ApiOperation({ summary: 'Edit a place. Changing published facts removes its publication until re-verified.' })
  async update(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    const reason = textField(b, 'reason', { max: 500, min: 5, required: true });
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const before = await q.one<Record<string, unknown> & { area_path: string | null; production_eligible: boolean }>(`${Q.ADMIN_PLACE_SQL} FOR UPDATE OF p`, [id]);
      if (!before) throw new NotFoundException('place not found');
      assertInScope(u, before.area_path);
      const f = await this.fields(q, b, false);
      if (f.area) assertInScope(u, f.area.path);
      const sets: string[] = [];
      const params: unknown[] = [id];
      const set = (col: string, val: unknown) => { params.push(val); sets.push(`${col} = $${params.length}`); };
      for (const [k, v] of Object.entries(f.v)) set(k, k === 'opening_hours' && v ? JSON.stringify(v) : v);
      if (f.cat) { set('category_id', f.cat.category_id); set('subcategory_id', f.cat.subcategory_id); }
      if (f.area) for (const k of ['division_id', 'district_id', 'upazila_id', 'union_id', 'city_corporation_id'] as const) set(k, f.area[k]);
      if (b.status !== undefined) {
        if (!STATUSES.includes(String(b.status))) throw new BadRequestException('invalid status');
        set('status', String(b.status));
      }
      if (!sets.length) throw new BadRequestException('nothing to change');
      const factual = Object.keys(f.v).some((k) => !['source_notes', 'data_source_id'].includes(k)) || !!f.cat || !!f.area;
      if (factual && before.production_eligible) {
        sets.push(`production_eligible = false, evidence_level = 'unverified', verification_notes = 'Edited; needs re-verification'`);
      }
      await q.many(`UPDATE places SET ${sets.join(', ')}, updated_at = now() WHERE id = $1`, params);
      const after = await q.one(Q.ADMIN_PLACE_SQL, [id]);
      await audit(q, { actor: u.id, action: 'place.update', entity: 'place', entityId: id, before, after, reason, requestId: req.id, ip: req.ip });
      return after;
    });
  }

  @Post('places/:id/verify')
  @RequireAuth('places.verify')
  async verify(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const before = await q.one<{ area_path: string | null }>(`${Q.ADMIN_PLACE_SQL} FOR UPDATE OF p`, [id]);
      if (!before) throw new NotFoundException('place not found');
      assertInScope(u, before.area_path);
      const v = await readVerify(q, body(raw));
      if (v.production_eligible) {
        const blocking = await q.many<{ id: number; match_score: number }>(DUP_BLOCKING_SQL, [id]);
        if (blocking.length) throw new BadRequestException(`suspected duplicate (score ${blocking[0]!.match_score}); resolve it under Duplicates before publishing`);
      }
      await q.many(
        `UPDATE places SET evidence_level = $2::evidence_level, evidence_source_id = $3, production_eligible = $4, verification_notes = $5,
           verification_status = CASE WHEN $2::text IN ('official','secondary') THEN 'verified' ELSE 'pending' END::verification_status,
           verified_by = $6, last_reviewed_at = now(), last_verified_at = CASE WHEN $2::text IN ('official','secondary') THEN current_date ELSE last_verified_at END,
           updated_at = now() WHERE id = $1`,
        [id, v.evidence_level, v.evidence_source_id, v.production_eligible, v.verification_notes, u.id]);
      const after = await q.one(Q.ADMIN_PLACE_SQL, [id]);
      await audit(q, { actor: u.id, action: 'place.verify', entity: 'place', entityId: id, before, after, reason: v.verification_notes, requestId: req.id, ip: req.ip });
      return after;
    });
  }

  /** Validated editable fields. `create` requires name_bn, category_key and area_id. */
  private async fields(q: Queryable, b: Record<string, unknown>, create: boolean) {
    const v: Record<string, unknown> = {};
    const text = (k: string, max: number, min?: number) => {
      if (b[k] === undefined) return;
      v[k] = textField(b, k, { max, min, required: create && k === 'name_bn' });
    };
    if (create && !b.name_bn) throw new BadRequestException('name_bn is required');
    text('name_bn', 160, 2); text('name_en', 160, 2); text('short_name', 30); text('address_bn', 300); text('address_en', 300);
    text('postcode', 10); text('email', 120); text('established', 30); text('description_bn', 2000); text('description_en', 2000); text('source_notes', 1000);
    if (b.website !== undefined) v.website = b.website ? urlField(b.website, 'website') : null;
    if (b.ownership !== undefined) {
      if (b.ownership !== null && !OWNERSHIP.includes(String(b.ownership))) throw new BadRequestException('invalid ownership');
      v.ownership = b.ownership;
    }
    if (b.lat !== undefined || b.lon !== undefined) {
      v.lat = b.lat == null ? null : floatParam(String(b.lat), 'lat', 20.3, 26.8);
      v.lon = b.lon == null ? null : floatParam(String(b.lon), 'lon', 88, 92.8);
      if ((v.lat === null) !== (v.lon === null)) throw new BadRequestException('lat and lon go together');
    }
    if (b.phones !== undefined) {
      if (!Array.isArray(b.phones) || b.phones.length > 6 || b.phones.some((p) => typeof p !== 'string' || !/^\+?[0-9\- ]{3,20}$/.test(p))) throw new BadRequestException('phones must be up to 6 numbers');
      v.phones = (b.phones as string[]).map((p) => p.trim());
    }
    if (b.opening_hours !== undefined) {
      if (b.opening_hours !== null && (typeof b.opening_hours !== 'object' || Array.isArray(b.opening_hours) || JSON.stringify(b.opening_hours).length > 2000)) throw new BadRequestException('opening_hours must be an object');
      v.opening_hours = b.opening_hours;
    }
    if (b.data_source_id !== undefined) v.data_source_id = b.data_source_id === null ? null : intParam(String(b.data_source_id), 'data_source_id', { min: 1 });
    let cat: ({ key: string } & Awaited<ReturnType<typeof categoryIds>>) | null = null;
    if (b.category_key !== undefined || create) {
      if (typeof b.category_key !== 'string') throw new BadRequestException('category_key is required');
      cat = { key: b.category_key, ...(await categoryIds(q, b.category_key)) };
    }
    let area: Awaited<ReturnType<typeof areaFks>> | null = null;
    if (b.area_id !== undefined || create) area = await areaFks(q, idParam(String(b.area_id ?? ''), 'area_id'));
    return { v, cat, area };
  }
}
