import { BadRequestException, Body, Controller, Get, NotFoundException, Param, Patch, Post, Query, Req } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { AdminStats, AuditEntry } from '@elaka360/shared';
import { Db, audit } from '../db/db.service';
import { CurrentUser, RequireAuth, assertInScope, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { body, floatParam, idParam, intParam, textField } from '../common/params';
import * as Q from './admin.sql';
import { EVIDENCE, boolQuery, page, paged, readVerify } from './admin.util';

const LEVEL_PARENT: Record<string, string[]> = {
  division: ['country'], district: ['division'], upazila: ['district'], city_corporation: ['district'],
  union: ['upazila'], pourashava: ['upazila'], ward: ['union', 'pourashava', 'city_corporation'],
};

@ApiTags('admin')
@Controller('v1/admin')
export class AdminAreasController {
  constructor(private readonly db: Db) {}

  @Get('stats')
  @RequireAuth('stats.read')
  @ApiOperation({ summary: 'Dashboard metrics, all computed live from the database' })
  async stats(): Promise<AdminStats> {
    const row = await this.db.one<Omit<AdminStats, 'recent_activity'>>(Q.ADMIN_STATS_SQL);
    const recent = await this.db.many<AuditEntry>(Q.AUDIT_LIST_SQL, [null, null, null, 10, 0]);
    const zero = Object.fromEntries(EVIDENCE.map((e) => [e, 0]));
    return {
      ...(row as Omit<AdminStats, 'recent_activity'>),
      areas_by_evidence: { ...zero, ...(row?.areas_by_evidence ?? {}) },
      places_by_evidence: { ...zero, ...(row?.places_by_evidence ?? {}) },
      recent_activity: recent,
    } as AdminStats;
  }

  @Get('areas')
  @RequireAuth('areas.read')
  async list(
    @CurrentUser() u: AuthUser, @Query('level') level?: string, @Query('parent_id') parent?: string, @Query('q') q?: string,
    @Query('evidence') evidence?: string, @Query('eligible') eligible?: string, @Query('limit') l?: string, @Query('cursor') c?: string,
  ) {
    if (evidence && !EVIDENCE.includes(evidence as never)) throw new BadRequestException('invalid evidence');
    const { limit, offset } = page(l, c);
    const rows = await this.db.many<{ total: number }>(Q.ADMIN_AREA_LIST_SQL, [
      level || null, intParam(parent, 'parent_id', { min: 1 }) ?? null, q?.trim().slice(0, 80) || null, evidence || null,
      boolQuery(eligible), u.scope_path, limit, offset]);
    return paged(rows, limit, offset);
  }

  @Get('areas/:id')
  @RequireAuth('areas.read')
  async get(@CurrentUser() u: AuthUser, @Param('id') id: string) {
    const area = await this.db.one<{ path: string; id: number }>(Q.ADMIN_AREA_SQL, [idParam(id)]);
    if (!area) throw new NotFoundException('area not found');
    assertInScope(u, area.path);
    const [children, history] = await Promise.all([
      this.db.many('SELECT level::text, count(*)::int AS n, count(*) FILTER (WHERE production_eligible)::int AS public FROM admin_areas WHERE parent_id = $1 GROUP BY 1', [area.id]),
      this.db.many<AuditEntry>(Q.AUDIT_LIST_SQL, ['admin_area', String(area.id), null, 50, 0]),
    ]);
    return { ...area, children, history };
  }

  @Patch('areas/:id')
  @RequireAuth('areas.edit')
  @ApiOperation({ summary: 'Edit names, codes, coordinates, status or parent (subtree paths follow); requires a reason' })
  async update(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    const reason = textField(b, 'reason', { max: 500, min: 5, required: true });
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const before = await q.one<Record<string, unknown> & { path: string; level: string; slug: string; parent_id: number }>(`${Q.ADMIN_AREA_SQL} FOR UPDATE OF a`, [id]);
      if (!before) throw new NotFoundException('area not found');
      assertInScope(u, before.path);
      const name_bn = textField(b, 'name_bn', { max: 120, min: 2 });
      const name_en = textField(b, 'name_en', { max: 120, min: 2 });
      const bbs = textField(b, 'bbs_code', { max: 20 });
      const website = textField(b, 'website', { max: 300 });
      const notes = textField(b, 'notes', { max: 2000 });
      const status = b.status === undefined ? null : ['active', 'inactive', 'archived'].includes(String(b.status)) ? String(b.status) : (() => { throw new BadRequestException('invalid status'); })();
      const lat = b.lat == null ? null : floatParam(String(b.lat), 'lat', 20.3, 26.8);
      const lon = b.lon == null ? null : floatParam(String(b.lon), 'lon', 88, 92.8);
      if (name_bn || name_en) {
        // A rename of a published record changes public facts: it must be re-verified.
        await q.many(`UPDATE admin_areas SET production_eligible = false, evidence_level = 'unverified', verified = false,
                      verification_notes = 'Renamed; needs re-verification' WHERE id = $1 AND production_eligible`, [id]);
      }
      await q.many(
        `UPDATE admin_areas SET name_bn = COALESCE($2, name_bn), name_en = COALESCE($3, name_en), bbs_code = COALESCE($4, bbs_code),
           website = COALESCE($5, website), notes = COALESCE($6, notes), status = COALESCE($7::record_status, status),
           lat = COALESCE($8, lat), lon = COALESCE($9, lon), updated_at = now() WHERE id = $1`,
        [id, name_bn, name_en, bbs, website, notes, status, lat, lon]);
      if (b.parent_id !== undefined) {
        const parentId = idParam(String(b.parent_id), 'parent_id');
        const parent = await q.one<{ id: number; level: string; path: string }>('SELECT id::int, level::text, path FROM admin_areas WHERE id = $1', [parentId]);
        if (!parent || !(LEVEL_PARENT[before.level] ?? []).includes(parent.level)) throw new BadRequestException(`a ${before.level} cannot sit under that parent`);
        if (parent.path === before.path || parent.path.startsWith(`${before.path}/`)) throw new BadRequestException('cannot move an area under itself');
        assertInScope(u, parent.path);
        const newPath = `${parent.path}/${before.slug}`;
        if (await q.one('SELECT 1 AS x FROM admin_areas WHERE path = $1 AND id <> $2', [newPath, id])) throw new BadRequestException('an area with that path already exists');
        await q.many('UPDATE admin_areas SET parent_id = $2 WHERE id = $1', [id, parentId]);
        await q.many(`UPDATE admin_areas SET path = $2 || substr(path, length($1) + 1) WHERE path = $1 OR path LIKE $1 || '/%'`, [before.path, newPath]);
      }
      const after = await q.one(Q.ADMIN_AREA_SQL, [id]);
      await audit(q, { actor: u.id, action: 'area.update', entity: 'admin_area', entityId: id, before, after, reason, requestId: req.id, ip: req.ip });
      return after;
    });
  }

  @Post('areas/:id/verify')
  @RequireAuth('areas.verify')
  @ApiOperation({ summary: 'Set evidence level, source and publication; enforced by the trust policy' })
  async verify(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const before = await q.one<{ path: string }>(`${Q.ADMIN_AREA_SQL} FOR UPDATE OF a`, [id]);
      if (!before) throw new NotFoundException('area not found');
      assertInScope(u, before.path);
      const v = await readVerify(q, body(raw));
      await q.many(
        `UPDATE admin_areas SET evidence_level = $2::evidence_level, evidence_source_id = $3, production_eligible = $4, verification_notes = $5,
           verified = ($2::text = 'official'), verified_by = $6, last_reviewed_at = now(), last_verified_at = CASE WHEN $2::text IN ('official','secondary') THEN current_date ELSE last_verified_at END,
           updated_at = now() WHERE id = $1`,
        [id, v.evidence_level, v.evidence_source_id, v.production_eligible, v.verification_notes, u.id]);
      const after = await q.one(Q.ADMIN_AREA_SQL, [id]);
      await audit(q, { actor: u.id, action: 'area.verify', entity: 'admin_area', entityId: id, before, after, reason: v.verification_notes, requestId: req.id, ip: req.ip });
      return after;
    });
  }

  @Get('audit')
  @RequireAuth('audit.read')
  async auditLog(@Query('entity') entity?: string, @Query('entity_id') entityId?: string, @Query('actor_id') actor?: string, @Query('limit') l?: string, @Query('cursor') c?: string) {
    const { limit, offset } = page(l, c);
    const items = await this.db.many<AuditEntry>(Q.AUDIT_LIST_SQL, [entity || null, entityId || null, intParam(actor, 'actor_id', { min: 1 }) ?? null, limit, offset]);
    return { items, next_cursor: items.length === limit ? Buffer.from(String(offset + limit)).toString('base64url') : null };
  }
}
