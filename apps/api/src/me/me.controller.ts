import { BadRequestException, Body, Controller, Delete, Get, HttpCode, NotFoundException, Param, Patch, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { Collection, Review, SavedItem } from '@elaka360/shared';
import { Db, audit } from '../db/db.service';
import { AuthService } from '../auth/auth.service';
import { CurrentUser, RequireAuth, type AuthUser } from '../common/auth/auth.guard';
import { body, idParam, intParam, normalisePath, textField } from '../common/params';

const SAVED_SQL = `
SELECT s.id::int, s.collection_id::int, to_char(s.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at,
  CASE WHEN p.id IS NULL THEN NULL ELSE json_build_object(
    'public_id', p.public_id, 'slug', p.slug, 'name_bn', p.name_bn, 'name_en', p.name_en, 'category_key', c.key,
    'subcategory_key', sc.key, 'area_label_bn', NULL, 'area_label_en', NULL, 'lat', p.lat::float8, 'lon', p.lon::float8,
    'verification_status', p.verification_status, 'evidence_level', p.evidence_level, 'production_eligible', p.production_eligible) END AS place,
  CASE WHEN a.id IS NULL THEN NULL ELSE json_build_object(
    'id', a.id, 'level', a.level, 'parent_id', a.parent_id, 'name_bn', a.name_bn, 'name_en', a.name_en, 'slug', a.slug,
    'path', a.path, 'verified', a.verified, 'evidence_level', a.evidence_level, 'production_eligible', a.production_eligible) END AS area
FROM saved_items s
LEFT JOIN public_places p ON p.id = s.place_id
LEFT JOIN categories c ON c.id = p.category_id
LEFT JOIN categories sc ON sc.id = p.subcategory_id
LEFT JOIN public_admin_areas a ON a.id = s.admin_area_id
WHERE s.user_id = $1 AND ($2::bigint IS NULL OR s.collection_id = $2) AND (p.id IS NOT NULL OR a.id IS NOT NULL)
ORDER BY s.created_at DESC
LIMIT 500`;

const COLLECTIONS_SQL = `
SELECT c.id::int, c.name, c.description, to_char(c.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at,
       (SELECT count(*)::int FROM saved_items s WHERE s.collection_id = c.id) AS item_count
FROM collections c WHERE c.user_id = $1 ORDER BY c.created_at`;

export const MY_REVIEWS_SQL = `
SELECT r.id::int, p.slug AS place_slug, r.rating, r.body, u.name AS author_name, true AS is_own,
       to_char(r.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at, to_char(r.updated_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS updated_at
FROM reviews r JOIN places p ON p.id = r.place_id JOIN users u ON u.id = r.user_id
WHERE r.user_id = $1 ORDER BY r.created_at DESC LIMIT 200`;

@ApiTags('me')
@Controller('v1/me')
@RequireAuth()
export class MeController {
  constructor(private readonly db: Db, private readonly auth: AuthService) {}

  @Get()
  me(@CurrentUser() u: AuthUser) {
    return this.auth.me(u.id);
  }

  @Patch()
  @ApiOperation({ summary: 'Update display name, home area or profile visibility' })
  async update(@CurrentUser() u: AuthUser, @Body() raw: unknown) {
    const b = body(raw);
    const name = textField(b, 'name', { max: 80, min: 2 });
    const homeId = b.home_area_id === undefined ? undefined : b.home_area_id === null ? null : intParam(String(b.home_area_id), 'home_area_id', { min: 1 });
    if (homeId) {
      const ok = await this.db.one('SELECT 1 AS ok FROM public_admin_areas WHERE id = $1', [homeId]);
      if (!ok) throw new BadRequestException('unknown home area');
    }
    const pub = typeof b.profile_public === 'boolean' ? b.profile_public : undefined;
    await this.db.many(
      `UPDATE users SET name = COALESCE($2, name), home_area_id = CASE WHEN $3::boolean THEN $4::bigint ELSE home_area_id END,
              profile_public = COALESCE($5, profile_public), updated_at = now() WHERE id = $1`,
      [u.id, name, homeId !== undefined, homeId ?? null, pub ?? null]);
    return this.auth.me(u.id);
  }

  @Post('deletion-request')
  @HttpCode(200)
  @ApiOperation({ summary: 'Ask for the account to be deleted (staff process it; cancel with DELETE)' })
  async requestDeletion(@CurrentUser() u: AuthUser) {
    await this.db.tx(async (q) => {
      await q.many('UPDATE users SET deletion_requested_at = now() WHERE id = $1', [u.id]);
      await audit(q, { actor: u.id, action: 'user.deletion_requested', entity: 'user', entityId: u.id });
    });
    return this.auth.me(u.id);
  }

  @Delete('deletion-request')
  async cancelDeletion(@CurrentUser() u: AuthUser) {
    await this.db.many('UPDATE users SET deletion_requested_at = NULL WHERE id = $1', [u.id]);
    return this.auth.me(u.id);
  }

  /* ---------- saved ---------- */

  @Get('saved')
  async saved(@CurrentUser() u: AuthUser, @Query('collection_id') col?: string): Promise<{ items: SavedItem[] }> {
    return { items: await this.db.many<SavedItem>(SAVED_SQL, [u.id, intParam(col, 'collection_id', { min: 1 }) ?? null]) };
  }

  @Post('saved')
  @ApiOperation({ summary: 'Save a public place (place_slug) or area (area_path); optional collection_id' })
  async save(@CurrentUser() u: AuthUser, @Body() raw: unknown) {
    const b = body(raw);
    const colId = b.collection_id == null ? null : intParam(String(b.collection_id), 'collection_id', { min: 1 })!;
    if (colId && !(await this.db.one('SELECT 1 AS ok FROM collections WHERE id = $1 AND user_id = $2', [colId, u.id]))) throw new NotFoundException('collection not found');
    let placeId: number | null = null;
    let areaId: number | null = null;
    if (typeof b.place_slug === 'string') {
      placeId = (await this.db.one<{ id: number }>('SELECT id::int FROM public_places WHERE slug = $1', [b.place_slug]))?.id ?? null;
      if (!placeId) throw new NotFoundException('place not found');
    } else if (typeof b.area_path === 'string') {
      areaId = (await this.db.one<{ id: number }>('SELECT id::int FROM public_admin_areas WHERE path = $1', [normalisePath(b.area_path)]))?.id ?? null;
      if (!areaId) throw new NotFoundException('area not found');
    } else throw new BadRequestException('place_slug or area_path is required');
    const row = await this.db.one<{ id: number }>(
      `INSERT INTO saved_items(user_id, collection_id, place_id, admin_area_id) VALUES ($1,$2,$3,$4)
       ON CONFLICT DO NOTHING RETURNING id::int`, [u.id, colId, placeId, areaId]);
    return { saved: true, id: row?.id ?? null };
  }

  @Delete('saved/:id')
  async unsave(@CurrentUser() u: AuthUser, @Param('id') id: string) {
    const r = await this.db.many('DELETE FROM saved_items WHERE id = $1 AND user_id = $2 RETURNING id', [idParam(id), u.id]);
    if (!r.length) throw new NotFoundException('saved item not found');
    return { removed: true };
  }

  @Delete('saved')
  @ApiOperation({ summary: 'Remove a saved place or area by place_slug / area_path query' })
  async unsaveByTarget(@CurrentUser() u: AuthUser, @Query('place_slug') slug?: string, @Query('area_path') path?: string) {
    if (!slug && !path) throw new BadRequestException('place_slug or area_path is required');
    await this.db.many(
      slug ? 'DELETE FROM saved_items s USING places p WHERE s.place_id = p.id AND p.slug = $2 AND s.user_id = $1'
           : 'DELETE FROM saved_items s USING admin_areas a WHERE s.admin_area_id = a.id AND a.path = $2 AND s.user_id = $1',
      [u.id, slug ?? normalisePath(path)]);
    return { removed: true };
  }

  @Get('collections')
  async collections(@CurrentUser() u: AuthUser): Promise<{ items: Collection[] }> {
    return { items: await this.db.many<Collection>(COLLECTIONS_SQL, [u.id]) };
  }

  @Post('collections')
  async createCollection(@CurrentUser() u: AuthUser, @Body() raw: unknown) {
    const b = body(raw);
    const count = await this.db.one<{ n: number }>('SELECT count(*)::int AS n FROM collections WHERE user_id = $1', [u.id]);
    if ((count?.n ?? 0) >= 50) throw new BadRequestException('collection limit reached');
    return this.db.one(`INSERT INTO collections(user_id, name, description) VALUES ($1,$2,$3) RETURNING id::int, name, description`,
      [u.id, textField(b, 'name', { max: 60, required: true }), textField(b, 'description', { max: 300 })]);
  }

  @Delete('collections/:id')
  async deleteCollection(@CurrentUser() u: AuthUser, @Param('id') id: string) {
    const r = await this.db.many('DELETE FROM collections WHERE id = $1 AND user_id = $2 RETURNING id', [idParam(id), u.id]);
    if (!r.length) throw new NotFoundException('collection not found');
    return { removed: true };
  }

  @Get('reviews')
  async reviews(@CurrentUser() u: AuthUser): Promise<{ items: Review[] }> {
    return { items: await this.db.many<Review>(MY_REVIEWS_SQL, [u.id]) };
  }
}
