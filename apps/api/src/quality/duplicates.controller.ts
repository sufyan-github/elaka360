import { BadRequestException, Body, Controller, Get, HttpCode, NotFoundException, Param, Post, Query, Req } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Db, audit, type Queryable } from '../db/db.service';
import { CurrentUser, RequireAuth, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { body, enumField, idParam, textField } from '../common/params';
import { page, paged } from '../admin/admin.util';
import { DUP_LIST_SQL } from './duplicates.sql';
import { findDuplicates, recordDuplicates } from './duplicates';

const DECISIONS = ['merged', 'kept_separate', 'not_duplicate', 'needs_more_review'] as const;

async function recomputeRating(q: Queryable, placeId: number) {
  await q.many(`UPDATE places SET rating_count = s.n, rating_avg = s.avg FROM (SELECT count(*)::int n, round(avg(rating)::numeric,1) avg
                FROM reviews WHERE place_id = $1 AND status = 'active') s WHERE places.id = $1`, [placeId]);
}

@ApiTags('admin')
@Controller('v1/admin/duplicates')
export class DuplicatesController {
  constructor(private readonly db: Db) {}

  @Get()
  @RequireAuth('places.read')
  @ApiOperation({ summary: 'Duplicate candidates, highest score first (status: open by default, or all)' })
  async list(@Query('status') status?: string, @Query('limit') l?: string, @Query('cursor') c?: string) {
    const st = status === 'all' ? null : status || 'open';
    if (st && !['open', ...DECISIONS].includes(st)) throw new BadRequestException('invalid status');
    const { limit, offset } = page(l, c);
    return paged(await this.db.many<{ total: number }>(DUP_LIST_SQL, [st, limit, offset]), limit, offset);
  }

  @Post('scan')
  @HttpCode(200)
  @RequireAuth('places.edit')
  @ApiOperation({ summary: 'Re-scan all active places for duplicates (records new pairs scoring ≥ 80)' })
  async scan(@CurrentUser() u: AuthUser, @Req() req: AuthedRequest) {
    return this.db.tx(async (q) => {
      const places = await q.many<{ id: number; name_bn: string; name_en: string | null; category_id: number; lat: number | null; lon: number | null }>(
        `SELECT id::int, name_bn, name_en, category_id, lat::float8, lon::float8 FROM places WHERE status = 'active' ORDER BY id LIMIT 20000`);
      const before = (await q.one<{ n: number }>('SELECT count(*)::int AS n FROM duplicate_candidates'))?.n ?? 0;
      for (const p of places) {
        // Only pair each place with older ones, so a pair is recorded once.
        const m = (await findDuplicates(q, { name_bn: p.name_bn, name_en: p.name_en, categoryId: p.category_id, lat: p.lat, lon: p.lon, excludeId: p.id }))
          .filter((x) => x.id < p.id);
        await recordDuplicates(q, m, { placeId: p.id });
      }
      const after = (await q.one<{ n: number }>('SELECT count(*)::int AS n FROM duplicate_candidates'))?.n ?? 0;
      await audit(q, { actor: u.id, action: 'duplicates.scan', entity: 'duplicate_candidates', entityId: 'all', after: { scanned: places.length, new_pairs: after - before }, requestId: req.id, ip: req.ip });
      return { scanned: places.length, new_pairs: after - before };
    });
  }

  @Post(':id/decision')
  @HttpCode(200)
  @RequireAuth('places.edit')
  @ApiOperation({ summary: 'merged (keeps place A; archives B and moves its reviews/saves, or rejects the duplicate contribution) | kept_separate | not_duplicate | needs_more_review' })
  async decide(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    const decision = enumField(b, 'decision', DECISIONS)!;
    const note = textField(b, 'note', { max: 1000, min: 3, required: true });
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const d = await q.one<{ a: number; b: number | null; contribution_id: number | null; status: string }>(
        'SELECT place_a_id::int AS a, place_b_id::int AS b, contribution_id::int, status::text FROM duplicate_candidates WHERE id = $1 FOR UPDATE', [id]);
      if (!d) throw new NotFoundException('candidate not found');
      if (d.status !== 'open' && d.status !== 'needs_more_review') throw new BadRequestException('already decided');
      if (decision === 'merged' && d.b) {
        await q.many(`UPDATE places SET status = 'archived', production_eligible = false, source_notes = concat_ws(' ', source_notes, $2::text), updated_at = now() WHERE id = $1`,
          [d.b, `[Merged into place #${d.a}]`]);
        await q.many('DELETE FROM saved_items s USING saved_items k WHERE s.place_id = $1 AND k.place_id = $2 AND k.user_id = s.user_id', [d.b, d.a]);
        await q.many('UPDATE saved_items SET place_id = $2 WHERE place_id = $1', [d.b, d.a]);
        await q.many('DELETE FROM reviews r USING reviews k WHERE r.place_id = $1 AND k.place_id = $2 AND k.user_id = r.user_id', [d.b, d.a]);
        await q.many('UPDATE reviews SET place_id = $2 WHERE place_id = $1', [d.b, d.a]);
        await recomputeRating(q, d.a);
      } else if (decision === 'merged' && d.contribution_id) {
        await q.many(`UPDATE contributions SET status = 'rejected', reviewer_id = $2, reviewer_note = $3, reviewed_at = now(), updated_at = now()
                      WHERE id = $1 AND status IN ('new', 'in_review', 'needs_changes')`, [d.contribution_id, u.id, `Duplicate of place #${d.a}: ${note}`]);
      }
      await q.many('UPDATE duplicate_candidates SET status = $2::duplicate_status, resolved_by = $3, resolved_at = CASE WHEN $2 = \'needs_more_review\' THEN NULL ELSE now() END WHERE id = $1',
        [id, decision, u.id]);
      await audit(q, { actor: u.id, action: `duplicate.${decision}`, entity: 'duplicate_candidate', entityId: id,
                       before: { status: d.status }, after: { status: decision, place_a: d.a, place_b: d.b, contribution: d.contribution_id }, reason: note, requestId: req.id, ip: req.ip });
      return { id, status: decision };
    });
  }
}
