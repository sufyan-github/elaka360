import { BadRequestException, Body, Controller, Get, NotFoundException, Param, Post, Query, Req } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { ContributionStatus } from '@elaka360/shared';
import { Db, audit } from '../db/db.service';
import { CurrentUser, RequireAuth, assertInScope, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { body, enumField, idParam, textField } from '../common/params';
import { ContributionsService, TYPES } from '../contributions/contributions.service';
import { areaFks, categoryIds } from './admin-places.controller';
import * as Q from './admin.sql';
import { page, paged } from './admin.util';

const POINTS_ON_APPROVAL = 10;
const PLACE_TYPES = new Set(['new_place', 'new_business', 'new_tourist_spot']);

@ApiTags('admin')
@Controller('v1/admin')
export class AdminModerationController {
  constructor(private readonly db: Db, private readonly contributions: ContributionsService) {}

  @Get('contributions')
  @RequireAuth('contributions.moderate')
  @ApiOperation({ summary: 'Moderation queue (scoped to your area), urgent first then oldest' })
  async queue(@CurrentUser() u: AuthUser, @Query('status') status?: string, @Query('type') type?: string, @Query('limit') l?: string, @Query('cursor') c?: string) {
    const { limit, offset } = page(l, c);
    if (type && !TYPES.includes(type as never)) throw new BadRequestException('invalid type');
    if (status && !['new', 'in_review', 'needs_changes', 'approved', 'rejected'].includes(status)) throw new BadRequestException('invalid status');
    const rows = await this.db.many<{ total: number }>(Q.ADMIN_CONTRIBUTIONS_SQL, [status || null, type || null, u.scope_path, limit, offset]);
    return paged(rows, limit, offset);
  }

  @Get('contributions/:id')
  @RequireAuth('contributions.moderate')
  async get(@CurrentUser() u: AuthUser, @Param('id') id: string) {
    const meta = await this.db.one<{ area_path: string | null }>(
      `SELECT c.area_path, c.priority, c.target_place_id::int, u.id::int AS submitter_id, u.name AS submitter_name
       FROM contributions c JOIN users u ON u.id = c.user_id WHERE c.id = $1`, [idParam(id)]);
    if (!meta) throw new NotFoundException('contribution not found');
    assertInScope(u, meta.area_path);
    return { ...(await this.contributions.get(idParam(id), null)), ...meta };
  }

  @Post('contributions/:id/decision')
  @RequireAuth('contributions.moderate')
  @ApiOperation({ summary: 'start_review | approve | request_changes | reject (note required except start_review)' })
  async decide(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    const decision = enumField(b, 'decision', ['start_review', 'approve', 'request_changes', 'reject'] as const)!;
    const note = textField(b, 'note', { max: 1000, min: 3, required: decision !== 'start_review' });
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const c = await q.one<{ status: ContributionStatus; type: string; user_id: number; area_path: string | null; payload: Record<string, unknown>; lat: number | null; lon: number | null }>(
        'SELECT status::text, type::text, user_id::int, area_path, payload, lat::float8, lon::float8 FROM contributions WHERE id = $1 FOR UPDATE', [id]);
      if (!c) throw new NotFoundException('contribution not found');
      assertInScope(u, c.area_path);
      if (c.user_id === u.id) throw new BadRequestException('you cannot moderate your own contribution');
      const allowed: Record<string, ContributionStatus[]> = {
        start_review: ['new'], approve: ['new', 'in_review'], request_changes: ['new', 'in_review'], reject: ['new', 'in_review', 'needs_changes'],
      };
      if (!allowed[decision]!.includes(c.status)) throw new BadRequestException(`cannot ${decision} a contribution that is ${c.status}`);
      const to: ContributionStatus = { start_review: 'in_review', approve: 'approved', request_changes: 'needs_changes', reject: 'rejected' }[decision] as ContributionStatus;
      let created: string | null = null;

      if (decision === 'approve' && PLACE_TYPES.has(c.type)) {
        // An approved suggestion becomes an unpublished place with community evidence; publication needs verification.
        const p = c.payload;
        const cat = await categoryIds(q, String(p.category_key));
        const areaId = typeof b.area_id === 'number' ? b.area_id : null;
        if (!areaId) throw new BadRequestException('area_id (the area the new place belongs to) is required to approve');
        const fk = await areaFks(q, areaId);
        assertInScope(u, fk.path);
        const seq = await q.one<{ n: number }>("SELECT nextval('places_id_seq')::int AS n");
        created = `${c.type === 'new_tourist_spot' ? 'TOUR' : c.type === 'new_business' ? 'BIZ' : 'INST'}-${String(seq!.n).padStart(8, '0')}`;
        await q.many(
          `INSERT INTO places(id, public_id, slug, name_bn, name_en, category_id, subcategory_id, ownership, division_id, district_id, upazila_id,
             union_id, city_corporation_id, address_bn, lat, lon, phones, website, description_bn, evidence_level, production_eligible,
             verification_status, source_notes, created_by)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,'community',false,'pending',$20,$21)`,
          [seq!.n, created, created.toLowerCase(), p.name_bn, p.name_en ?? null, cat.category_id, cat.subcategory_id,
           ['public', 'private', 'ngo', 'trust', 'autonomous'].includes(String(p.ownership)) ? p.ownership : null,
           fk.division_id, fk.district_id, fk.upazila_id, fk.union_id, fk.city_corporation_id, p.address ?? null, c.lat, c.lon,
           Array.isArray(p.phones) ? p.phones : [], p.website ?? null, p.description ?? null, `From contribution #${id}`, c.user_id]);
      }

      await q.many(
        `UPDATE contributions SET status = $2::contribution_status, reviewer_id = $3, reviewer_note = COALESCE($4, reviewer_note), updated_at = now(),
           reviewed_at = CASE WHEN $2::text IN ('approved','rejected','needs_changes') THEN now() ELSE reviewed_at END,
           points_awarded = CASE WHEN $2::text = 'approved' THEN $5 ELSE points_awarded END WHERE id = $1`,
        [id, to, u.id, created ? `${note ?? ''} [created ${created}]`.trim() : note, POINTS_ON_APPROVAL]);
      await q.many('INSERT INTO contribution_events(contribution_id, actor_id, from_status, to_status, note) VALUES ($1,$2,$3::contribution_status,$4::contribution_status,$5)', [id, u.id, c.status, to, note]);
      if (decision === 'approve') {
        await q.many(`UPDATE users SET points = points + $2,
                        level = (SELECT max(level) FROM levels WHERE min_points <= users.points + $2) WHERE id = $1`, [c.user_id, POINTS_ON_APPROVAL]);
        await q.many(`INSERT INTO notifications(user_id, kind, title, body) VALUES ($1, 'contribution', 'আপনার অবদান অনুমোদিত হয়েছে', $2)`, [c.user_id, note]);
      } else if (decision !== 'start_review') {
        await q.many(`INSERT INTO notifications(user_id, kind, title, body) VALUES ($1, 'contribution', $2, $3)`,
          [c.user_id, decision === 'reject' ? 'আপনার অবদান গ্রহণ করা যায়নি' : 'আপনার অবদানে সংশোধন প্রয়োজন', note]);
      }
      await audit(q, { actor: u.id, action: `contribution.${decision}`, entity: 'contribution', entityId: id, before: { status: c.status }, after: { status: to, created_place: created }, reason: note, requestId: req.id, ip: req.ip });
      return this.contributions.get(id, null, q);
    });
  }

  @Get('review-reports')
  @RequireAuth('reviews.moderate')
  async reports(@Query('status') status?: string) {
    return { items: await this.db.many(Q.ADMIN_REVIEW_REPORTS_SQL, [status === 'all' ? null : status || 'open']) };
  }

  @Post('review-reports/:id/decision')
  @RequireAuth('reviews.moderate')
  @ApiOperation({ summary: 'uphold (hides the review) or dismiss a report' })
  async decideReport(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    const decision = enumField(b, 'decision', ['uphold', 'dismiss'] as const)!;
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const r = await q.one<{ review_id: number; place_id: number; status: string }>(
        'SELECT rr.review_id::int, r.place_id::int, rr.status FROM review_reports rr JOIN reviews r ON r.id = rr.review_id WHERE rr.id = $1 FOR UPDATE OF rr', [id]);
      if (!r) throw new NotFoundException('report not found');
      if (r.status !== 'open') throw new BadRequestException('report already decided');
      await q.many('UPDATE review_reports SET status = $2 WHERE review_id = $1 AND status = \'open\'', [r.review_id, decision === 'uphold' ? 'upheld' : 'dismissed']);
      if (decision === 'uphold') {
        await q.many(`UPDATE reviews SET status = 'inactive' WHERE id = $1`, [r.review_id]);
        await q.many(`UPDATE places SET rating_count = s.n, rating_avg = s.avg FROM (SELECT count(*)::int n, round(avg(rating)::numeric,1) avg
                      FROM reviews WHERE place_id = $1 AND status = 'active') s WHERE places.id = $1`, [r.place_id]);
      }
      await audit(q, { actor: u.id, action: `review_report.${decision}`, entity: 'review', entityId: r.review_id, requestId: req.id, ip: req.ip });
      return { decided: decision };
    });
  }
}
