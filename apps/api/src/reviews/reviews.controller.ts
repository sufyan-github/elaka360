import { BadRequestException, Body, ConflictException, Controller, Delete, Get, HttpCode, HttpException, HttpStatus, NotFoundException, Param, Patch, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Throttle } from '@nestjs/throttler';
import type { Review } from '@elaka360/shared';
import { Db, type Queryable } from '../db/db.service';
import { PlacesService } from '../places/places.service';
import { CurrentUser, RequireAuth, type AuthUser } from '../common/auth/auth.guard';
import { body, cursor, idParam, intParam, textField } from '../common/params';

const REVIEWS_SQL = `
SELECT r.id::int, $2::text AS place_slug, r.rating, r.body, u.name AS author_name, (r.user_id = $3) AS is_own,
       to_char(r.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at, to_char(r.updated_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS updated_at
FROM public_reviews r JOIN users u ON u.id = r.user_id
WHERE r.place_id = $1 AND u.status = 'active'
ORDER BY r.created_at DESC LIMIT $4 OFFSET $5`;

const RECOMPUTE_SQL = `
UPDATE places SET rating_count = s.n, rating_avg = s.avg, updated_at = now()
FROM (SELECT count(*)::int AS n, round(avg(rating)::numeric, 1) AS avg FROM reviews WHERE place_id = $1 AND status = 'active') s
WHERE places.id = $1`;

function rating(v: unknown): number {
  const n = Number(v);
  if (!Number.isInteger(n) || n < 1 || n > 5) throw new BadRequestException('rating must be 1 to 5');
  return n;
}

@ApiTags('reviews')
@Controller('v1')
export class ReviewsController {
  constructor(private readonly db: Db, private readonly places: PlacesService) {}

  @Get('places/:slug/reviews')
  @ApiOperation({ summary: 'Public reviews of a place (newest first)' })
  async list(@Param('slug') slug: string, @CurrentUser() u?: AuthUser, @Query('limit') l?: string, @Query('cursor') c?: string) {
    const id = await this.places.idOf(slug);
    const limit = intParam(l, 'limit', { min: 1, max: 50, def: 20 })!;
    const offset = cursor.decode(c);
    const items = await this.db.many<Review>(REVIEWS_SQL, [id, slug, u?.id ?? 0, limit, offset]);
    return { items, next_cursor: items.length === limit ? cursor.encode(offset + limit) : null };
  }

  @Post('places/:slug/reviews')
  @RequireAuth()
  @Throttle({ default: { limit: 5, ttl: 60_000 } })
  @ApiOperation({ summary: 'Add your review (one per place; 10 per day)' })
  async create(@Param('slug') slug: string, @CurrentUser() u: AuthUser, @Body() raw: unknown) {
    const b = body(raw);
    const r = rating(b.rating);
    const text = textField(b, 'body', { max: 2000 });
    const placeId = await this.places.idOf(slug);
    const today = await this.db.one<{ n: number }>(`SELECT count(*)::int AS n FROM reviews WHERE user_id = $1 AND created_at > now() - interval '1 day'`, [u.id]);
    if ((today?.n ?? 0) >= 10) throw new HttpException('daily review limit reached', HttpStatus.TOO_MANY_REQUESTS);
    return this.db.tx(async (q) => {
      const row = await q.one<{ id: number }>(
        `INSERT INTO reviews(place_id, user_id, rating, body) VALUES ($1,$2,$3,$4) ON CONFLICT (place_id, user_id) DO NOTHING RETURNING id::int`,
        [placeId, u.id, r, text]);
      if (!row) throw new ConflictException('you have already reviewed this place; edit your review instead');
      await q.many(RECOMPUTE_SQL, [placeId]);
      return { id: row.id };
    });
  }

  @Patch('reviews/:id')
  @RequireAuth()
  async update(@Param('id') id: string, @CurrentUser() u: AuthUser, @Body() raw: unknown) {
    const b = body(raw);
    return this.db.tx(async (q) => {
      const row = await this.own(q, idParam(id), u.id);
      await q.many(`UPDATE reviews SET rating = COALESCE($2, rating), body = CASE WHEN $3::boolean THEN $4 ELSE body END, updated_at = now() WHERE id = $1`,
        [row.id, b.rating === undefined ? null : rating(b.rating), b.body !== undefined, textField(b, 'body', { max: 2000 })]);
      await q.many(RECOMPUTE_SQL, [row.place_id]);
      return { updated: true };
    });
  }

  @Delete('reviews/:id')
  @RequireAuth()
  async remove(@Param('id') id: string, @CurrentUser() u: AuthUser) {
    return this.db.tx(async (q) => {
      const row = await this.own(q, idParam(id), u.id);
      await q.many('DELETE FROM reviews WHERE id = $1', [row.id]);
      await q.many(RECOMPUTE_SQL, [row.place_id]);
      return { removed: true };
    });
  }

  @Post('reviews/:id/report')
  @HttpCode(200)
  @RequireAuth()
  @Throttle({ default: { limit: 10, ttl: 60_000 } })
  @ApiOperation({ summary: 'Report a review for moderation' })
  async report(@Param('id') id: string, @CurrentUser() u: AuthUser, @Body() raw: unknown) {
    const reason = textField(body(raw), 'reason', { max: 500, min: 3, required: true });
    const exists = await this.db.one('SELECT 1 AS ok FROM public_reviews WHERE id = $1', [idParam(id)]);
    if (!exists) throw new NotFoundException('review not found');
    await this.db.many(`INSERT INTO review_reports(review_id, reporter_id, reason) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING`, [idParam(id), u.id, reason]);
    return { reported: true };
  }

  private async own(q: Queryable, id: number, userId: number) {
    const row = await q.one<{ id: number; place_id: number; user_id: number }>('SELECT id::int, place_id::int, user_id::int FROM reviews WHERE id = $1 FOR UPDATE', [id]);
    if (!row || row.user_id !== userId) throw new NotFoundException('review not found');
    return row;
  }
}
